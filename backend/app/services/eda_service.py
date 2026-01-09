import pandas as pd
import numpy as np
import math
from app.services.data_service import DataService

class EdaService:
    @staticmethod
    def get_basic_stats(df):
        """
        Returns descriptive statistics for all columns.
        """
        # df passed in directly
        stats = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            col_stats = {
                'name': col,
                'type': dtype,
                'count': int(df[col].count()),
                'missing': int(df[col].isnull().sum())
            }
            
            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats.update({
                    'mean': float(df[col].mean()) if not df[col].isnull().all() else None,
                    'std': float(df[col].std()) if not df[col].isnull().all() else None,
                    'min': float(df[col].min()) if not df[col].isnull().all() else None,
                    'max': float(df[col].max()) if not df[col].isnull().all() else None,
                    'q25': float(df[col].quantile(0.25)) if not df[col].isnull().all() else None,
                    'q50': float(df[col].median()) if not df[col].isnull().all() else None,
                    'q75': float(df[col].quantile(0.75)) if not df[col].isnull().all() else None,
                })
            else:
                # Categorical stats
                vc = df[col].value_counts().head(5)
                col_stats['top_values'] = vc.index.tolist()
                col_stats['top_counts'] = vc.values.tolist()
                col_stats['unique_count'] = int(df[col].nunique())

            stats.append(col_stats)
            
        return DataService.sanitize_for_json(stats)

    @staticmethod
    def get_correlation(df):
        """
        Returns correlation matrix for numerical columns.
        """
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return {'columns': [], 'matrix': []}

        corr_matrix = numeric_df.corr(method='pearson')
        
        # Prepare for Heatmap: x, y, z
        columns = list(corr_matrix.columns)
        z = corr_matrix.where(pd.notnull(corr_matrix), 0).values.tolist() # Replace NaN corr with 0
        
        return DataService.sanitize_for_json({
            'columns': columns,
            'matrix': z
        })

    @staticmethod
    def get_distribution(df, column, bins=20):
        """
        Returns histogram data for a specific column.
        """
        if column not in df.columns:
            return None

        series = df[column].dropna()
        if series.empty:
            return None

        if pd.api.types.is_numeric_dtype(series):
            hist, bin_edges = np.histogram(series, bins=bins)
            return DataService.sanitize_for_json({
                'type': 'numerical',
                'x': [(bin_edges[i] + bin_edges[i+1])/2 for i in range(len(hist))], # bin centers
                'y': hist.tolist()
            })
        else:
            vc = series.value_counts().head(20) # Limit to top 20
            return DataService.sanitize_for_json({
                'type': 'categorical',
                'x': vc.index.tolist(),
                'y': vc.values.tolist()
            })
