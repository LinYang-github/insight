
from flask import Blueprint, jsonify
from app.services.validation_service import ValidationService

validation_bp = Blueprint('validation', __name__, url_prefix='/api/validation')

@validation_bp.route('/run', methods=['POST'])
def run_validation():
    """
    Trigger full validation suite (Scientific + Robustness).
    """
    report = {}
    
    # 1. Scientific
    scientific_res = ValidationService.run_scientific_validation()
    report['scientific'] = scientific_res
    
    # 2. Robustness
    robustness_res = ValidationService.run_robustness_checks()
    report['robustness'] = robustness_res
    
    # Calculate overall status
    # Simple logic: if any item has status FAIL, then overall FAIL
    all_items = scientific_res + robustness_res
    failed_items = [x for x in all_items if x['status'] == 'FAIL']
    
    report['summary'] = {
        'total_tests': len(all_items),
        'passed': len(all_items) - len(failed_items),
        'failed': len(failed_items),
        'status': 'PASS' if len(failed_items) == 0 else 'FAIL'
    }
    
    return jsonify(report)

@validation_bp.route('/benchmarks', methods=['GET'])
def get_benchmarks():
    """
    Return the static definition of benchmarks (for frontend display).
    """
    return jsonify(ValidationService.get_r_benchmarks())
