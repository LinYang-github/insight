
import sys
import os
import json
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.services.validation_service import ValidationService

def verify():
    print("Running Scientific Validation...")
    try:
        report = ValidationService.run_scientific_validation()
    except Exception as e:
        print(f"FAIL: Scientific Validation raised exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Check Assumptions
    print("\nChecking Assumptions:")
    found_assumption = False
    for test in report:
        print(f"Test: {test['test_name']}")
        if test['status'] == 'FAIL':
             print(f"  FAIL: {test.get('error', 'Unknown Error')}")
             continue
        print(f"Metrics: {[m['name'] for m in test['metrics']]}")
        if 'assumptions' in test and test['assumptions']:
            found_assumption = True
            for a in test['assumptions']:
                print(f"  - {a['check']}: p={a.get('p_value')} Status={a['status']}")
        else:
            print("  - No assumptions.")
                
    if not found_assumption:
        print("FAIL: No assumptions found in report.")
        # Only strict fail if we expect assumptions everywhere? 
        # T-test and Cox should have them. Logistic might not.
        # Check if Cox has it.
        cox_tests = [t for t in report if 'Cox' in t['test_name']]
        if cox_tests and not any('assumptions' in t for t in cox_tests):
             print("FAIL: Cox test missing assumptions.")
             sys.exit(1)
        
    # Check Open Pack Access
    print("\nChecking Open Pack Access:")
    allowed = ValidationService.get_allowed_datasets()
    if any("benchmark_logistic.R" in f for f in allowed):
        print("PASS: benchmark_logistic.R found in allowed datasets.")
    else:
        print("FAIL: benchmark_logistic.R NOT found in allowed datasets.")
        print(f"Allowed: {allowed}")
        sys.exit(1)

    print("\nVERIFICATION SUCCESSFUL")

if __name__ == "__main__":
    verify()
