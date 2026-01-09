
import numpy as np
from sklearn.metrics import roc_curve, auc, accuracy_score, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.calibration import calibration_curve
from app.utils.formatter import ResultFormatter

class ModelEvaluator:
    @staticmethod
    def evaluate_classification(y_true, y_prob, y_pred=None):
        """
        Calculates classification metrics and plot data.
        :param y_true: True labels (0/1)
        :param y_prob: Predicted probabilities for class 1
        :param y_pred: Predicted labels (optional, can be derived from prob>0.5)
        :return: (metrics_dict, plots_dict)
        """
        if y_pred is None:
            y_pred = (y_prob >= 0.5).astype(int)
            
        metrics = {}
        plots = {}
        
        # 1. Basic Metrics
        metrics['accuracy'] = ResultFormatter.format_float(accuracy_score(y_true, y_pred), 4)
        metrics['precision'] = ResultFormatter.format_float(precision_score(y_true, y_pred, zero_division=0), 4)
        metrics['recall'] = ResultFormatter.format_float(recall_score(y_true, y_pred, zero_division=0), 4)
        metrics['f1'] = ResultFormatter.format_float(f1_score(y_true, y_pred, zero_division=0), 4)
        
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        
        # 2. ROC Curve & AUC
        if len(np.unique(y_true)) == 2:
            fpr, tpr, _ = roc_curve(y_true, y_prob)
            roc_auc = auc(fpr, tpr)
            metrics['auc'] = ResultFormatter.format_float(roc_auc, 3)
            
            plots['roc'] = {
                'fpr': fpr.tolist(),
                'tpr': tpr.tolist(),
                'auc': roc_auc
            }
            
            # 3. Calibration Curve
            prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)
            plots['calibration'] = {
                'prob_true': prob_true.tolist(),
                'prob_pred': prob_pred.tolist()
            }
            
            # 4. Decision Curve Analysis (DCA)
            dca_res = ModelEvaluator.calculate_dca(y_true, y_prob)
            plots['dca'] = dca_res
            
        return metrics, plots

    @staticmethod
    def calculate_dca(y_true, y_prob):
        """
        Calculate Decision Curve Analysis (Net Benefit).
        """
        thresholds = np.arange(0.01, 1.0, 0.01)
        net_benefit_model = []
        net_benefit_all = []
        
        n = len(y_true)
        n_p = np.sum(y_true) # Total positives
        n_n = n - n_p        # Total negatives
        
        for p_t in thresholds:
            # Model Benefit
            y_pred_t = (y_prob >= p_t).astype(int)
            tp = np.sum((y_pred_t == 1) & (y_true == 1))
            fp = np.sum((y_pred_t == 1) & (y_true == 0))
            
            nb_model = (tp / n) - (fp / n) * (p_t / (1 - p_t))
            net_benefit_model.append(nb_model)
            
            # Treat All Benefit
            # TP = n_p, FP = n_n
            nb_all = (n_p / n) - (n_n / n) * (p_t / (1 - p_t))
            net_benefit_all.append(nb_all)
            
        return {
            'thresholds': thresholds.tolist(),
            'net_benefit_model': net_benefit_model,
            'net_benefit_all': net_benefit_all,
            'net_benefit_none': [0] * len(thresholds) # Treat None is always 0
        }

    @staticmethod
    def evaluate_regression(y_true, y_pred):
        # Placeholder for completeness if needed later
        pass
