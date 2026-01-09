
import pandas as pd
import numpy as np
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from app.utils.formatter import ResultFormatter

class ModelDiagnostics:
    @staticmethod
    def calculate_vif(df, features):
        """
        Calculate Variance Inflation Factor (VIF) for features.
        """
        if not features or len(features) < 2:
            return []
            
        try:
            X = df[features].copy()
            # Handle categoricals if not already encoded? 
            # ModelingService normally receives original DF, strategies handle encoding.
            # But specific strategies (Linear/Logistic) in this project use statsmodels formulae or 
            # assume numeric/dummy encoding if using sklearn style? 
            # Let's check LinearRegressionStrategy.fit logic.
            # It selects X = df[features]. 
            # If features are categorical strings, statsmodels `OLS(y, X)` might fail or auto-encode if formula used.
            # But the current implementation `X = df[features]; X = sm.add_constant(X); model = sm.OLS(y, X)` 
            # implies input features MUST be numeric.
            # The `TreeModelStrategy` handles encoding explicitly.
            # `LinearRegressionStrategy` in `linear.py` assumes numeric inputs for now (Stage 1 assumption).
            # If not, VIF will fail.
            # We will assume numeric for VIF calculation now, consistent with current LinearStrategy.
            
            # Drop rows with NaNs for VIF calc
            X = X.dropna()
            X = add_constant(X)
            
            vif_data = []
            for i, col in enumerate(X.columns):
                if col == 'const': continue
                # Handle singular matrix or errors in VIF
                try:
                    val = variance_inflation_factor(X.values, i)
                    vif_data.append({
                        'variable': col,
                        'vif': ResultFormatter.format_float(val, 2) if not np.isinf(val) else 'Inf'
                    })
                except Exception:
                    vif_data.append({'variable': col, 'vif': 'Error'})
            
            return vif_data
        except Exception as e:
            print(f"VIF Calculation failed: {e}")
            return []
