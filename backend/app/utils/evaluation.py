"""
app.utils.evaluation.py

工具模块：评估模型预测性能。
包含分类指标（ROC/AUC）、校准曲线（Calibration Curve）和决策曲线分析（DCA）。
"""
import numpy as np
from sklearn.metrics import roc_curve, auc, accuracy_score, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.calibration import calibration_curve
from app.utils.formatter import ResultFormatter

class ModelEvaluator:
    @staticmethod
    def evaluate_classification(y_true, y_prob, y_pred=None):
        """
        计算分类模型的评估指标及其绘图数据。

        Args:
            y_true (np.array): 结局变量真实值 (0/1)。
            y_prob (np.array): 模型预测的概率（Class 1 的概率）。
            y_pred (np.array, optional): 模型预测的分类标签。如果未提供，默认以 0.5 为阈值。

        Returns:
            tuple: (metrics_dict, plots_dict) 包含准确率、召回率、AUC及ROC/校准曲线数据。
        """
        if y_pred is None:
            y_pred = (y_prob >= 0.5).astype(int)
            
        metrics = {}
        plots = {}
        
        # 1. 基础指标 (Accuracy, Precision, Recall, F1)
        metrics['accuracy'] = ResultFormatter.format_float(accuracy_score(y_true, y_pred), 4)
        metrics['precision'] = ResultFormatter.format_float(precision_score(y_true, y_pred, zero_division=0), 4)
        metrics['recall'] = ResultFormatter.format_float(recall_score(y_true, y_pred, zero_division=0), 4)
        metrics['f1'] = ResultFormatter.format_float(f1_score(y_true, y_pred, zero_division=0), 4)
        
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        
        # 2. ROC 曲线与 AUC
        if len(np.unique(y_true)) == 2:
            fpr, tpr, _ = roc_curve(y_true, y_prob)
            roc_auc = auc(fpr, tpr)
            metrics['auc'] = ResultFormatter.format_float(roc_auc, 3)
            
            plots['roc'] = {
                'fpr': fpr.tolist(),
                'tpr': tpr.tolist(),
                'auc': roc_auc
            }
            
            # 3. 校准曲线 (Calibration Curve)
            prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)
            plots['calibration'] = {
                'prob_true': prob_true.tolist(),
                'prob_pred': prob_pred.tolist()
            }
            
            # 4. 决策曲线分析 (DCA)
            dca_res = ModelEvaluator.calculate_dca(y_true, y_prob)
            plots['dca'] = dca_res
            
        return metrics, plots

    @staticmethod
    def calculate_dca(y_true, y_prob):
        """
        计算决策曲线分析 (DCA, Decision Curve Analysis)。
        
        DCA 不仅考量模型的预测准确性，更关注模型在临床决策中的“净获益” (Net Benefit)。
        通过对比“全部干预”、“全不干预”与“模型指导下干预”的净获益，评估模型的临床实用价值。

        Args:
            y_true (np.array): 结局变量真实值 (0/1)。
            y_prob (np.array): 模型预测的概率。

        Returns:
            dict: 包含不同阈值概率下的净获益数据，用于前端 Plotly 绘图。
        """
        thresholds = np.arange(0.01, 1.0, 0.01)
        net_benefit_model = []
        net_benefit_all = []
        
        n = len(y_true)
        n_p = np.sum(y_true) # 阳性样本总量
        n_n = n - n_p        # 阴性样本总量
        
        for p_t in thresholds:
            # 模型干预的净获益 (Model Benefit)
            y_pred_t = (y_prob >= p_t).astype(int)
            tp = np.sum((y_pred_t == 1) & (y_true == 1))
            fp = np.sum((y_pred_t == 1) & (y_true == 0))
            
            nb_model = (tp / n) - (fp / n) * (p_t / (1 - p_t))
            net_benefit_model.append(nb_model)
            
            # 全体干预的净获益 (Treat All Benefit)
            # TP = n_p, FP = n_n
            nb_all = (n_p / n) - (n_n / n) * (p_t / (1 - p_t))
            net_benefit_all.append(nb_all)
            
        return {
            'thresholds': thresholds.tolist(),
            'net_benefit_model': net_benefit_model,
            'net_benefit_all': net_benefit_all,
            'net_benefit_none': [0] * len(thresholds) # 全不干预的净获益恒为 0
        }

    @staticmethod
    def evaluate_regression(y_true, y_pred):
        # Placeholder for completeness if needed later
        pass
