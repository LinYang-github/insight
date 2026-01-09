
import numpy as np

class ResultFormatter:
    @staticmethod
    def format_p_value(p_value):
        """
        Formats P-value according to APA style.
        P < 0.001 -> "<0.001"
        Otherwise 3 decimal places.
        """
        if p_value is None or np.isnan(p_value):
            return "N/A"
        if p_value < 0.001:
            return "<0.001"
        return f"{p_value:.3f}"

    @staticmethod
    def format_float(val, precision=3):
        """
        Formats float with specific precision.
        """
        if val is None or np.isnan(val):
            return None
        return float(f"{val:.{precision}f}")
