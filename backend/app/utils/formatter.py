"""
app.utils.formatter.py

工具模块：负责统计结果的标准化格式化。
确保 P 值、回归系数等在显示给用户前符合医学学术规范。
"""
import pandas as pd
import numpy as np

class ResultFormatter:
    @staticmethod
    def format_p_value(p_value):
        """
        按照 APA 学术规范格式化 P 值。
        P < 0.001 显示为 "<0.001"，其余保留 3 位小数。
        """
        if pd.isna(p_value):
            return "N/A"
        if p_value < 0.001:
            return "<0.001"
        return f"{p_value:.3f}"

    @staticmethod
    def format_float(val, precision=3):
        """
        Formats float with specific precision.
        """
        if val is None:
            return None
        # Handle numpy / list types
        if isinstance(val, (list, tuple, np.ndarray)):
            # If single element, extract it
            if np.size(val) == 1:
                val = np.array(val).item()
            else:
                # Cannot format array
                return val
        
        if pd.isna(val):
            return None
        return float(f"{val:.{precision}f}")
