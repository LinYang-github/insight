
from typing import Dict, Type
from .base import BaseModelStrategy

class ModelRegistry:
    _strategies: Dict[str, Type[BaseModelStrategy]] = {}
    _instance_cache: Dict[str, BaseModelStrategy] = {}

    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseModelStrategy]):
        cls._strategies[name] = strategy_class

    @classmethod
    def get_strategy(cls, name: str) -> BaseModelStrategy:
        if name not in cls._strategies:
            raise ValueError(f"Model type '{name}' is not registered.")
        
        if name not in cls._instance_cache:
            cls._instance_cache[name] = cls._strategies[name]()
            
        return cls._instance_cache[name]
