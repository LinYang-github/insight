import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, auc
from sklearn.calibration import calibration_curve

class EvaluationService:
    """
    Service for advanced clinical model evaluation metrics and plotting data.
    Includes:
    - DCA (Decision Curve Analysis)
    - Calibration Curves
    - Time-Dependent ROC (for Survival, handled partially here or passed through)
    """

    @staticmethod
    def calculate_dca(y_true, y_prob, thresholds=None):
        """
        Calculate Net Benefit for Decision Curve Analysis (Binary).
        
        Args:
            y_true: array-like of true binary labels (0/1)
            y_prob: array-like of predicted probabilities
            thresholds: array-like of probability thresholds [0, 1]
            
        Returns:
            dict: { 'thresholds': [], 'net_benefit': [], 'net_benefit_all': [], 'net_benefit_none': [] }
        """
        if thresholds is None:
            thresholds = np.linspace(0.01, 0.99, 99)
            
        y_true = np.array(y_true)
        y_prob = np.array(y_prob)
        N = len(y_true)
        event_rate = np.mean(y_true)
        
        net_benefits = []
        net_benefit_all = [] # Treat all as positive
        net_benefit_none = np.zeros(len(thresholds)) # Treat none as positive (NB=0)
        
        for thresh in thresholds:
            # Model Net Benefit
            y_pred = (y_prob >= thresh).astype(int)
            tp = np.sum((y_pred == 1) & (y_true == 1))
            fp = np.sum((y_pred == 1) & (y_true == 0))
            
            nb = (tp / N) - (fp / N) * (thresh / (1 - thresh))
            net_benefits.append(nb)
            
            # Treat All Net Benefit
            # TP_all = Total Positives, FP_all = Total Negatives
            tp_all = np.sum(y_true == 1)
            fp_all = np.sum(y_true == 0)
            nb_all = (tp_all / N) - (fp_all / N) * (thresh / (1 - thresh))
            net_benefit_all.append(nb_all)
            
        return {
            'thresholds': thresholds.tolist(),
            'net_benefit_model': net_benefits,
            'net_benefit_all': net_benefit_all,
            'net_benefit_none': net_benefit_none.tolist()
        }

    @staticmethod
    def calculate_calibration(y_true, y_prob, n_bins=10):
        """
        Calculate Calibration Curve (Binary).
        
        Returns:
            dict: { 'prob_pred': [], 'prob_true': [] }
        """
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy='uniform')
        return {
            'prob_pred': prob_pred.tolist(),
            'prob_true': prob_true.tolist()
        }

    @staticmethod
    def calculate_survival_calibration(model, df, duration_col, event_col, time_point, n_bins=5):
        """
        Calculate Calibration for Survival Model (Cox) at a specific time point.
        Uses KM estimate for observed probability in each bin.
        """
        try:
            # 1. Predict survival probability at time_point
            # lifelines: predict_survival_function returns DataFrame where index=time, col=patient
            surv_df = model.predict_survival_function(df, times=[time_point])
            # Probability of Survival score (S(t))
            # Probability of Event = 1 - S(t)
            prob_event = 1 - surv_df.iloc[0].values 
            
            # 2. Binning based on predicted risk
            # Create quantiles
            df_temp = df.copy()
            df_temp['prob_event'] = prob_event
            df_temp['bin'] = pd.qcut(df_temp['prob_event'], n_bins, duplicates='drop', labels=False)
            
            calibration_data = {
                'prob_pred': [],
                'prob_true': []
            }
            
            from lifelines import KaplanMeierFitter
            kmf = KaplanMeierFitter()
            
            valid_bins = sorted(df_temp['bin'].unique())
            
            for b in valid_bins:
                bin_data = df_temp[df_temp['bin'] == b]
                if len(bin_data) == 0:
                    continue
                
                # Mean predicted probability in this bin
                mean_pred = bin_data['prob_event'].mean()
                
                # Observed probability: 1 - KM(time_point)
                kmf.fit(bin_data[duration_col], bin_data[event_col])
                # Ensure time_point is within range or take last
                if time_point > kmf.survival_function_.index.max():
                     obs_surv = kmf.survival_function_.iloc[-1, 0]
                else:
                     # Get closest index
                     idx = kmf.survival_function_.index.get_indexer([time_point], method='nearest')[0]
                     obs_surv = kmf.survival_function_.iloc[idx, 0]
                
                obs_event = 1 - obs_surv
                
                calibration_data['prob_pred'].append(mean_pred)
                calibration_data['prob_true'].append(obs_event)
                
            return calibration_data
            
        except Exception as e:
            print(f"Survival calibration failed: {e}")
            return {'prob_pred': [], 'prob_true': []}

    @staticmethod
    def calculate_survival_dca(model, df, duration_col, event_col, time_point, thresholds=None):
        """
        Calculate Net Benefit for Survival Model at specific time point.
        Uses 'Time-Fixed' approximation:
        - If T < t and E=1: Case (Positive)
        - If T > t: Control (Negative)
        - If T < t and E=0: Censored (Excluded from standard binary DCA, or use specific weighting)
        
        Ideally, should use weighting (IPCW). For MVP simplicity, we might filter censored 
        before t (which biases), or just use simple binary approx if censorship is low.
        
        Better MVP approach:
        Predict 1-S(t) as probability.
        Status at t:
           1 if duration <= t && event == 1
           0 if duration > t 
           NaN if duration <= t && event == 0 (Censored before t - unknown status)
           
        We remove patients censored before t for the calculation (Simple Complete Case).
        """
        if thresholds is None:
            thresholds = np.linspace(0.01, 0.99, 99)
            
        # 1. Predict risk
        surv_df = model.predict_survival_function(df, times=[time_point])
        prob_event = 1 - surv_df.iloc[0].values
        
        # 2. Define Outcome at time t
        # Filter out subjects censored before t
        # Keep: (duration > t) OR (duration <= t AND event = 1)
        mask = (df[duration_col] > time_point) | ((df[duration_col] <= time_point) & (df[event_col] == 1))
        
        df_eval = df[mask].copy()
        y_prob = prob_event[mask]
        
        # y_true: 1 if duration <= t (and implicit event=1 due to mask), 0 otherwise
        y_true = (df_eval[duration_col] <= time_point).astype(int)
        
        return EvaluationService.calculate_dca(y_true, y_prob, thresholds)

    @staticmethod
    def _calculate_proportion_ci(count, nobs, alpha=0.05):
        if nobs == 0: return 0.0, 0.0
        # Wilson approximation if statsmodels missing, or manual implementation
        # p = count / nobs
        # z = 1.96
        # ...
        # For simplicity and speed, use statsmodels if available, else Normal Approx
        try:
             import statsmodels.stats.proportion as proportion
             l, h = proportion.proportion_confint(count, nobs, alpha=alpha, method='wilson')
             return float(l), float(h)
        except:
             # Fallback: Normal Approx (Simpler but less robust for small N, better than crash)
             p = count / nobs
             se = np.sqrt(p * (1 - p) / nobs)
             return max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)

    @staticmethod
    def calculate_binary_metrics_at_threshold(y_true, y_prob):
        """
        Calculate Se, Sp, PPV, NPV, Youden, AUC and their 95% CIs.
        """
        fpr, tpr, thresholds = roc_curve(y_true, y_prob)
        
        # Calculate Youden Index for all thresholds
        # Youden = TPR - FPR = TPR - (1 - Specificity) = Sensitivity + Specificity - 1
        youden_indices = tpr - fpr
        best_idx = np.argmax(youden_indices)
        best_threshold = thresholds[best_idx]
        max_youden = youden_indices[best_idx]
        
        # Binary predictions at best threshold
        y_pred = (y_prob >= best_threshold).astype(int)
        
        from sklearn.metrics import confusion_matrix, roc_auc_score
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        # Point Estimates
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        
        # AUC & CI (Hanley & McNeil 1982)
        try:
            auc = roc_auc_score(y_true, y_prob)
            n1 = np.sum(y_true == 1)
            n2 = np.sum(y_true == 0)
            if n1 > 0 and n2 > 0:
                q1 = auc / (2 - auc)
                q2 = 2 * auc**2 / (1 + auc)
                se_auc = np.sqrt(((auc * (1 - auc)) + (n1 - 1)*(q1 - auc**2) + (n2 - 1)*(q2 - auc**2)) / (n1 * n2))
                auc_ci_lower = max(0.0, auc - 1.96 * se_auc)
                auc_ci_upper = min(1.0, auc + 1.96 * se_auc)
            else:
                 auc_ci_lower, auc_ci_upper = 0.0, 0.0
        except:
            auc = 0.5
            auc_ci_lower, auc_ci_upper = 0.0, 0.0

        # Intervals
        sen_l, sen_h = EvaluationService._calculate_proportion_ci(tp, tp+fn)
        spe_l, spe_h = EvaluationService._calculate_proportion_ci(tn, tn+fp)
        ppv_l, ppv_h = EvaluationService._calculate_proportion_ci(tp, tp+fp)
        npv_l, npv_h = EvaluationService._calculate_proportion_ci(tn, tn+fn)

        return {
            'optimal_threshold': float(best_threshold),
            'sensitivity': float(sensitivity), 'sensitivity_ci_lower': sen_l, 'sensitivity_ci_upper': sen_h,
            'specificity': float(specificity), 'specificity_ci_lower': spe_l, 'specificity_ci_upper': spe_h,
            'ppv': float(ppv), 'ppv_ci_lower': ppv_l, 'ppv_ci_upper': ppv_h,
            'npv': float(npv), 'npv_ci_lower': npv_l, 'npv_ci_upper': npv_h,
            'youden_index': float(max_youden),
            'auc': float(auc), 'auc_ci_lower': auc_ci_lower, 'auc_ci_upper': auc_ci_upper
        }

    @staticmethod
    def calculate_brier_score(y_true, y_prob):
        """
        Calculate Brier Score for binary outcomes.
        """
        from sklearn.metrics import brier_score_loss
        return brier_score_loss(y_true, y_prob)

    @staticmethod
    def calculate_survival_metrics_at_t(model, df, duration_col, event_col, time_point):
        """
        Calculate advanced metrics (Se, Sp, Brier) for Survival Model at T.
        Uses exclusion mask for censoring before T (Concurrent Validity).
        """
        # 1. Predict 1-S(t)
        surv_df = model.predict_survival_function(df, times=[time_point])
        prob_event = 1 - surv_df.iloc[0].values
        
        # 2. Mask
        mask = (df[duration_col] > time_point) | ((df[duration_col] <= time_point) & (df[event_col] == 1))
        df_eval = df[mask]
        y_prob = prob_event[mask]
        y_true = (df_eval[duration_col] <= time_point).astype(int)
        
        if len(y_true) == 0:
            return {}
            
        # Binary Metrics (Se, Sp, etc.)
        binary_res = EvaluationService.calculate_binary_metrics_at_threshold(y_true, y_prob)
        
        # Brier Score
        brier = EvaluationService.calculate_brier_score(y_true, y_prob)
        
        # Merge
        binary_res['brier_score'] = float(brier)
        binary_res['n_events'] = int(y_true.sum())
        binary_res['n_eval'] = int(len(y_true))
        
        # GND Test (Simplified Chi-Square of Deciles)
        # Reuse logic from calibration
        try:
            calib = EvaluationService.calculate_survival_calibration(model, df, duration_col, event_col, time_point, n_bins=10)
            # calib has mean_pred and obs_event (prob_true)
            # Need N per bin to calculate counts
            # Re-running binning locally is safer or return N in calibration
            # Simplification: Skip formal P-value for now, Brier score is main calibration metric requested.
            pass
        except:
            pass
            
        return binary_res

    @staticmethod
    def calculate_nri_idi(y_true, p_old, p_new):
        """
        Calculate Continuous NRI and IDI with SE and P-value.
        """
        from scipy.stats import norm
        
        y_true = np.array(y_true)
        p_old = np.array(p_old)
        p_new = np.array(p_new)
        
        # Masks
        event_mask = (y_true == 1)
        nonevent_mask = (y_true == 0)
        
        n_events = np.sum(event_mask)
        n_nonevents = np.sum(nonevent_mask)
        
        if n_events == 0 or n_nonevents == 0:
            return {}
            
        # --- NRI (Continuous) ---
        # Event Group
        p_up_e = np.mean(p_new[event_mask] > p_old[event_mask])
        p_down_e = np.mean(p_new[event_mask] < p_old[event_mask])
        nri_e = p_up_e - p_down_e
        
        # Non-Event Group
        p_down_ne = np.mean(p_new[nonevent_mask] < p_old[nonevent_mask])
        p_up_ne = np.mean(p_new[nonevent_mask] > p_old[nonevent_mask])
        nri_ne = p_down_ne - p_up_ne
        
        nri = nri_e + nri_ne
        
        # SE for NRI
        # Var(NRI_e) = (p_up + p_down - (p_up - p_down)^2) / N
        var_e = (p_up_e + p_down_e - nri_e**2) / n_events
        var_ne = (p_down_ne + p_up_ne - nri_ne**2) / n_nonevents
        se_nri = np.sqrt(var_e + var_ne)
        
        z_nri = nri / se_nri if se_nri > 0 else 0
        p_nri = 2 * (1 - norm.cdf(abs(z_nri)))
        
        # CI
        nri_lower = nri - 1.96 * se_nri
        nri_upper = nri + 1.96 * se_nri
        
        # --- IDI ---
        diff = p_new - p_old
        idi_e = np.mean(diff[event_mask])
        idi_ne = np.mean(diff[nonevent_mask])
        idi = idi_e - idi_ne
        
        # SE for IDI
        # SE = sqrt( SE_diff_e^2 + SE_diff_ne^2 )
        se_diff_e = np.std(diff[event_mask], ddof=1) / np.sqrt(n_events)
        se_diff_ne = np.std(diff[nonevent_mask], ddof=1) / np.sqrt(n_nonevents)
        se_idi = np.sqrt(se_diff_e**2 + se_diff_ne**2)
        
        z_idi = idi / se_idi if se_idi > 0 else 0
        p_idi = 2 * (1 - norm.cdf(abs(z_idi)))
        
        idi_lower = idi - 1.96 * se_idi
        idi_upper = idi + 1.96 * se_idi
        
        return {
            'nri': float(nri),
            'nri_p': float(p_nri),
            'nri_ci': f"{nri_lower:.3f}-{nri_upper:.3f}",
            'idi': float(idi),
            'idi_p': float(p_idi),
            'idi_ci': f"{idi_lower:.3f}-{idi_upper:.3f}"
        }

    @staticmethod
    def calculate_delong_test(y_true, p_base, p_new):
        """
        Perform DeLong Test to compare two correlated ROC curves (AUC).
        H0: AUC_base == AUC_new
        
        Ref: DeLong et al. (1988). Comparing the Areas under Two or More Correlated Receiver Operating Characteristic Curves.
        """
        import scipy.stats as stats
        
        y_true = np.array(y_true)
        p_base = np.array(p_base)
        p_new = np.array(p_new)
        
        # Indices of positive and negative examples
        pos_idx = np.where(y_true == 1)[0]
        neg_idx = np.where(y_true == 0)[0]
        
        m = len(pos_idx)
        n = len(neg_idx)
        
        if m == 0 or n == 0:
            return {'p_delong': '-', 'z_delong': '-'}

        # Calculate AUCs & V-matrix via Covariance
        # Fast DeLong Implementation adapted for 2 models
        
        def compute_mid_rank(x):
            J = np.argsort(x)
            Z = x[J]
            N = len(x)
            T = np.zeros(N, dtype=float)
            i = 0
            while i < N:
                j = i
                while j < N and Z[j] == Z[i]:
                    j += 1
                T[i:j] = 0.5 * (i + j - 1)
                i = j
            T2 = np.empty(N, dtype=float)
            T2[J] = T + 1
            return T2

        # V10: for each positive case, average rank among negatives (divided by n)
        # V01: for each negative case, average rank among positives (divided by m)
        
        def calculate_variance_components(preds):
            V10 = []
            V01 = []
            aucs = []
            
            for p in preds:
                X = p[pos_idx] # Predictions for cases
                Y = p[neg_idx] # Predictions for controls
                
                # Fast Mann-Whitney / V-stat
                # Rank of X in merged(X, Y)
                # But DeLong formulation uses structural components
                # Structural Component V10[i] = (1/n) * sum_j I(X_i > Y_j) + 0.5 I(X_i = Y_j)
                # This is equivalent to (Rank(X_i) in Combined - Rank(X_i) in X) / n ???
                # No, simpler: 
                # Let's use the mid-rank formula.
                # W = Mann-Whitney Stat. AUC = W / (m*n)
                
                # Vectorized V10 calculation
                # Concatenate [X_i, Ys] ... slow for O(N^2)
                # Use global rank approach:
                # R_combined = rank of X in (X U Y)
                # sum I(X_i > Y_j) = R_combined(X_i) - R_self(X_i)  ? No.
                
                # Correct approach using mid-ranks on pooled data
                pooled = np.concatenate([X, Y])
                ranks = compute_mid_rank(pooled)
                rank_X = ranks[:m]
                rank_Y = ranks[m:]
                
                # AUC
                auc = (np.sum(rank_X) - 0.5 * m * (m + 1)) / (m * n)
                aucs.append(auc)
                
                # V10_i = ( 1/n ) * ( R(X_i) - R_X(X_i) ) ? 
                # Actually: V10_i = (Rank of X_i among Y + X_i) - (Rank of X_i among X) ...
                # Formula: V10_i = (sum_{j=1}^n psi(X_i, Y_j)) / n
                # where psi(u, v) = 1 if u > v, 0.5 if u = v.
                # psi(X_i, Y_j) is exactly Mann-Whitney kernel.
                # sum_j psi(X_i, Y_j) = (Rank of X_i in pooled) - (Rank of X_i in X)
                
                ranks_in_X = compute_mid_rank(X)
                v10 = (rank_X - ranks_in_X) / n
                V10.append(v10)
                
                # V01_j = (sum_{i=1}^m psi(X_i, Y_j)) / m
                # sum_i psi(X_i, Y_j) = m - sum_i psi(Y_j, X_i)
                # sum_i psi(Y_j, X_i) = (Rank of Y_j in pooled) - (Rank of Y_j in Y)
                ranks_in_Y = compute_mid_rank(Y)
                v01 = (1.0 - (rank_Y - ranks_in_Y) / m)
                V01.append(v01)
                
            return np.array(V10).T, np.array(V01).T, np.array(aucs)

        V10, V01, aucs = calculate_variance_components([p_base, p_new])
        
        # Covariance Matrix S
        # S = (1/m) * Cov(V10) + (1/n) * Cov(V01)
        S_10 = np.cov(V10, rowvar=False)
        S_01 = np.cov(V01, rowvar=False)
        
        S = (S_10 / m) + (S_01 / n)
        
        # Variance of difference (A - B)
        # Var(d) = S[0,0] + S[1,1] - 2*S[0,1]
        
        var_diff = S[0,0] + S[1,1] - 2*S[0,1]
        
        if var_diff <= 1e-9:
             z_score = 0.0
             p_val = 1.0
        else:
             z_score = (aucs[1] - aucs[0]) / np.sqrt(var_diff)
             p_val = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        return {
            'auc_base': float(aucs[0]),
            'auc_new': float(aucs[1]),
            'p_delong': float(p_val),
            'z_delong': float(z_score),
            'var_diff': float(var_diff)
        }
