try:
    from app.services.evaluation_service import EvaluationService
    from app.modeling.linear import LogisticRegressionStrategy
    from app.modeling.survival import CoxStrategy
    print("Imports successful")
except Exception as e:
    print(e)
