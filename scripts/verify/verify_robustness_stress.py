
import sys
import os
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

from app.services.validation_service import ValidationService

def verify_robustness():
    print("\n[Robustness Check - Singularity detection]")
    # This might print specific error logs from run_robustness_checks
    checks = ValidationService.run_robustness_checks()
    
    # Find "Perfect Multicollinearity" case
    multicoll_case = next((c for c in checks if "Perfect Multicollinearity" in c['case']), None)
    
    if not multicoll_case:
        print("FAIL: Robustness case 'Perfect Multicollinearity' not found.")
        sys.exit(1)
        
    print(f"Case Status: {multicoll_case['status']}")
    print(f"Message: {multicoll_case['message']}")
    
    if multicoll_case['status'] != 'PASS':
        print("FAIL: Expected PASS for Perfect Multicollinearity detection.")
        sys.exit(1)
    else:
        print("PASS: Successfully detected singular matrix.")

def verify_stress_test():
    print("\n[Stress Test API Check]")
    # 1. Collinearity
    res1 = ValidationService.run_stress_test("logistic", "collinearity", 5.0)
    print(f"Stress (Collinearity) Status: {res1['result']['status']}")
    # It might pass (if ridge) or fail? 
    # With severity 5.0 and noise, it might just run but have high VIF.
    # The requirement is that it runs and returns a result.
    if 'result' not in res1:
        print("FAIL: Invalid response structure.")
        sys.exit(1)

    # 2. Outliers
    res2 = ValidationService.run_stress_test("logistic", "outliers", 2.0)
    print(f"Stress (Outliers) Status: {res2['result']['status']}")
    if res2['result']['status'] != 'SUCCESS':
         print(f"WARN: Stress test failed to converge (this is allowed in stress test).")
    
    print("PASS: Stress Test API executed.")

if __name__ == "__main__":
    try:
        verify_robustness()
        verify_stress_test()
        print("\nROBUSTNESS & STRESS VERIFICATION SUCCESSFUL")
    except Exception as e:
        print(f"\nFAIL: Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
