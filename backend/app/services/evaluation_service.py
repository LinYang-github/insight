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
