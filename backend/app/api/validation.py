
from flask import Blueprint, jsonify, send_from_directory, request, send_file
from app.services.validation_service import ValidationService

validation_bp = Blueprint('validation', __name__, url_prefix='/api/validation')

@validation_bp.route('/run', methods=['POST'])
def run_validation():
    """
    Trigger full validation suite (Scientific + Robustness).
    Optional JSON params: {"use_large_dataset": true}
    """
    params = request.get_json() or {}
    use_large = params.get('use_large_dataset', False)

    report = {}
    
    # 1. Scientific
    scientific_res = ValidationService.run_scientific_validation(use_large_dataset=use_large)
    report['scientific'] = scientific_res
    
    # 2. Robustness
    robustness_res = ValidationService.run_robustness_checks()
    report['robustness'] = robustness_res
    
    # Calculate overall status
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

@validation_bp.route('/data/<filename>', methods=['GET'])
def download_validation_data(filename):
    """
    Download a specific validation dataset.
    """
    # Security check using allowlist
    allowed = ValidationService.get_allowed_datasets()
    if filename not in allowed:
         return jsonify({"error": "File not found or access denied"}), 404
         
    return send_from_directory(
        ValidationService.GOLDEN_DATA_DIR, 
        filename, 
        as_attachment=True
    )

@validation_bp.route('/stress-test', methods=['POST'])
def run_stress_test():
    """
    Run an interactive stress test.
    Input: {"dataset": "logistic", "fault": "collinearity", "severity": 1.0}
    """
    params = request.get_json() or {}
    dataset = params.get('dataset', 'logistic')
    fault = params.get('fault', 'collinearity')
    severity = params.get('severity', 1.0)
    
    result = ValidationService.run_stress_test(dataset, fault, severity)
    return jsonify(result)

@validation_bp.route('/report', methods=['POST'])
def download_report():
    """
    Generate PDF report from JSON data.
    """
    report_data = request.get_json()
    if not report_data:
        return jsonify({"error": "No report data provided"}), 400
    
    pdf_buffer = ValidationService.generate_pdf_report(report_data)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name='Insight_Validation_Report.pdf',
        mimetype='application/pdf'
    )
