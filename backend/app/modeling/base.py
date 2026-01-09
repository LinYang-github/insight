
from abc import ABC, abstractmethod
import pandas as pd

class BaseModelStrategy(ABC):
    @abstractmethod
    def fit(self, df: pd.DataFrame, target: any, features: list, params: dict) -> dict:
        """
        Fit the model and return formatted results.
        :param df: Training data
        :param target: Target variable name (str) or dict for survival
        :param features: List of feature names
        :param params: Model parameters
        :return: Standardized result dictionary
        """
        pass
