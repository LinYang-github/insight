
from app.services.data_service import DataService
from app.modeling.registry import ModelRegistry
from app.modeling.linear import LinearRegressionStrategy, LogisticRegressionStrategy
from app.modeling.survival import CoxStrategy
from app.modeling.tree import RandomForestStrategy, XGBoostStrategy
import numpy as np
import pandas as pd

# Register Strategies
ModelRegistry.register('linear', LinearRegressionStrategy)
ModelRegistry.register('logistic', LogisticRegressionStrategy)
ModelRegistry.register('cox', CoxStrategy)
ModelRegistry.register('random_forest', RandomForestStrategy)
ModelRegistry.register('xgboost', XGBoostStrategy)

class ModelingService:
    @staticmethod
    def check_data_integrity(df, features, target):
        """
        Checks for NaNs, Infs in features and target.
        Also checks for Zero Variance (Constant columns).
        """
        # Check features missing
        if df[features].isnull().any().any():
            missing_cols = df[features].columns[df[features].isnull().any()].tolist()
            raise ValueError(f"Feature variables contain missing values (NaN): {', '.join(missing_cols)}. Please impute missing values in 'Data Cleaning' first.")
            
        # Check features inf
        if np.isinf(df[features].select_dtypes(include=np.number)).values.any():
             raise ValueError("Feature variables contain infinite values. Please check your data.")
             
        # Check Zero Variance (Constant Columns)
        # Note: Categorical columns with 1 unique value are also constant
        for col in features:
            if df[col].nunique() <= 1:
                raise ValueError(f"Variable '{col}' is constant (variance=0). It contains only one unique value and cannot be used for modeling.")

        # Check target
        if isinstance(target, str):
            if df[target].isnull().any():
                raise ValueError(f"Target variable '{target}' contains missing values.")
        elif isinstance(target, dict): # Cox time/event
            if df[target['time']].isnull().any() or df[target['event']].isnull().any():
                 raise ValueError("Target variables (Time/Event) contain missing values.")

    @staticmethod
    def run_model(df, model_type, target, features, model_params=None):
        """
        Run statistical or ML model using Strategy Pattern.
        """
        model_params = model_params or {}
        
        # 1. Integrity Check
        ModelingService.check_data_integrity(df, features, target)
        
        # 2. Get Strategy
        try:
            strategy = ModelRegistry.get_strategy(model_type)
        except ValueError as e:
            raise ValueError(f"Unknown model type: {model_type}")
            
        # 3. Execute
        try:
            results = strategy.fit(df, target, features, model_params)
        except np.linalg.LinAlgError:
              raise ValueError("Linear Algebra Error: Singular matrix detected. Please check for perfect multi-collinearity among your variables.")
        except Exception as e:
            if isinstance(e, ValueError): raise e
            raise RuntimeError(f"Model execution failed: {str(e)}")

        return DataService.sanitize_for_json(results)
