"""
app.utils.metadata_builder.py

负责构建统计分析结果的元数据 (Metadata)。
用于向前端传递“为什么选择这个检验方法”、“模型假设检验结果”等解释性信息。
"""

class MetadataBuilder:
    @staticmethod
    def build_test_meta(test_name, reason=None, assumption_checks=None):
        """
        构建假设检验的元数据。

        Args:
            test_name (str): 检验方法名称 (e.g., "Welch's T-test").
            reason (str): 选择该方法的理由 (e.g., "方差验证显著 (P=0.01)，不满足方差齐性假设").
            assumption_checks (list): 具体的假设检验结果列表.
        
        Returns:
            dict: 标准化的元数据字典.
        """
        meta = {
            "test_name": test_name,
            "algorithm_type": "hypothesis_test"
        }
        
        if reason:
            meta["selection_reason"] = reason
            
        if assumption_checks:
            meta["assumptions"] = assumption_checks
            
        return meta

    @staticmethod
    def build_model_meta(model_name, formula, warnings=None):
        """
        构建统计模型的元数据.
        """
        meta = {
            "model_name": model_name,
            "formula": formula,
            "algorithm_type": "statistical_model"
        }
        
        if warnings:
            meta["warnings"] = warnings
            
        return meta
