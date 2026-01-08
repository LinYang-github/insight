import pandas as pd
import os
from flask import current_app

class ExportService:
    @staticmethod
    def export_results_to_excel(results, filename):
        """
        Export modeling results to Excel.
        :param results: dict of results (summary, metrics) from ModelingService
        :param filename: desired filename
        :return: absolute path to saved file
        """
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Create Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Summary sheet
            if 'summary' in results:
                df_summary = pd.DataFrame(results['summary'])
                df_summary.to_excel(writer, sheet_name='Model Summary', index=False)
                
            # Metrics sheet
            if 'metrics' in results:
                # Convert dict to DataFrame
                df_metrics = pd.DataFrame([results['metrics']])
                df_metrics.to_excel(writer, sheet_name='Metrics', index=False)
                
        return filepath
