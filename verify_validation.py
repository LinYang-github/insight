
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.services.validation_service import ValidationService

def test_generate_pdf():
    print("Testing PDF Generation...")
    dummy_report = {
        'summary': {'status': 'PASS', 'total_tests': 10, 'passed': 10},
        'scientific': [
            {
                'test_name': 'Test A',
                'metrics': [
                    {'name': 'Metric 1', 'value_insight': 1.0, 'value_r': 1.0, 'value_sas': 1.0, 'delta': 0.0, 'pass': True}
                ]
            }
        ]
    }
    
    try:
        pdf = ValidationService.generate_pdf_report(dummy_report)
        print(f"PDF Generated. Size: {len(pdf.getvalue())} bytes")
        with open("test_report.pdf", "wb") as f:
            f.write(pdf.getvalue())
        print("Written to test_report.pdf")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    test_generate_pdf()
