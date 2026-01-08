import pandas as pd
import numpy as np
import os
import math

class DataService:
    @staticmethod
    def get_initial_metadata(filepath):
        """
        Reads a CSV/Excel file and returns metadata:
        - columns: list of column names
        - types: inferred types (continuous, categorical)
        - preview: first 5 rows
        """
        if filepath.endswith('.csv'):
            # Roboust parsing with encoding detection
            encodings = ['utf-8', 'gb18030', 'latin1']
            df = None
            for encoding in encodings:
                try:
                    # low_memory=False to avoid DtypeWarning and ensure accurate parsing
                    df = pd.read_csv(filepath, encoding=encoding, low_memory=False)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Failed to parse CSV file with supported encodings (utf-8, gb18030, latin1)")
        elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            df = pd.read_excel(filepath)
        else:
            raise ValueError("Unsupported file format")
            
        metadata = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            var_type = 'continuous' if 'int' in dtype or 'float' in dtype else 'categorical'
            
            # Heuristic: if categorical has too many unique values, might be ID or text
            if var_type == 'categorical' and df[col].nunique() > 50:
                 var_type = 'text/id'
            
            # Heuristic: if numeric has few unique values (e.g. 0/1), might be categorical
            if var_type == 'continuous' and df[col].nunique() < 10:
                var_type = 'categorical'

            metadata.append({
                'name': col,
                'type': var_type, # continuous, categorical, ordinal, etc.
                'role': 'covariate', # default role
                'missing_count': int(df[col].isnull().sum()),
                'unique_count': int(df[col].nunique())
            })
            
            
        # Replace NaN with None for valid JSON serialization
        # Use a robust sanitization helper
        raw_result = {
            'variables': metadata,
            'row_count': len(df),
            'preview': df.head().to_dict(orient='records')
        }
        return DataService.sanitize_for_json(raw_result)

    @staticmethod
    def sanitize_for_json(obj):
        """
        Recursively sanitizes values for JSON serialization:
        - NaNs / Infs -> None
        - Numpy ints/floats -> Python ints/floats
        """
        if isinstance(obj, dict):
            return {k: DataService.sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DataService.sanitize_for_json(v) for v in obj]
        elif isinstance(obj, float):
            if pd.isna(obj) or math.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, int): # covers numpy integers if they inherit from int (some do)
             return int(obj)
        elif hasattr(obj, 'item'): # numpy types like np.int64, np.float32
            val = obj.item()
            if isinstance(val, float) and (pd.isna(val) or math.isinf(val)):
                return None
            return val
        elif pd.isna(obj): # pd.NA, np.nan (if not caught by float)
            return None
        return obj
