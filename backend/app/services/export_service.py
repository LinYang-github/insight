"""
app.services.export_service.py

导出服务。
负责将统计分析与建模结果导出为 Excel 格式，便于用户撰写论文或进行离线分析。
"""
import pandas as pd
import os
from flask import current_app

class ExportService:
    @staticmethod
    def export_results_to_excel(results, filename):
        """
        将模型结果导出为 Excel 文件。

        Args:
            results (dict): ModelingService 返回的模型结果字典。
            filename (str): 目标文件名。

        Returns:
            str: 导出文件的绝对路径。
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
