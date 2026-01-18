import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

try:
    from app.services.evaluation_service import EvaluationService
    from app.modeling.linear import LogisticRegressionStrategy
    from app.modeling.survival import CoxStrategy
    print("Imports successful")
except Exception as e:
    print(e)