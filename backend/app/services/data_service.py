"""
app.services.data_service.py

负责基础数据操作。
包含稳健的 CSV/Excel 加载、元数据自动提取以及 JSON 序列化前的脱敏处理。
"""
import pandas as pd
import numpy as np
import os
import math

class DataService:
    @staticmethod
    def load_data(filepath):
        """
        稳健地加载数据（支持 CSV, Excel）。
        
        针对 CSV 格式，自动尝试 utf-8, gb18030 等多种编码，确保中文无乱码。
        使用 low_memory=False 保证大文件解析的准确性。
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
            return df
        elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            return pd.read_excel(filepath)
        else:
            raise ValueError("Unsupported file format (only .csv, .xlsx, .xls)")

    @staticmethod
    def get_initial_metadata(filepath):
        """
        读取并生成数据集的初始元数据。

        Args:
            filepath (str): 数据文件路径。

        Returns:
            dict: 包含变量列表、类型推断、缺失值统计及数据预览的字典。
        """
        df = DataService.load_data(filepath)
            
        metadata = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            var_type = 'continuous' if 'int' in dtype or 'float' in dtype else 'categorical'
            
            # 启发式规则：如果分类变量唯一值过多，可能是 ID 或 文本
            if var_type == 'categorical' and df[col].nunique() > 50:
                 var_type = 'text/id'
            
            # 启发式规则：如果数值变量唯一值很少（如 0/1），可能是分类变量
            if var_type == 'continuous' and df[col].nunique() < 10:
                var_type = 'categorical'

            metadata.append({
                'name': col,
                'type': var_type,
                'role': 'covariate',
                'missing_count': int(df[col].isnull().sum()),
                'unique_count': int(df[col].nunique()),
                # Add categories for dropdowns (limit to 50 to avoid payload explosion)
                'categories': df[col].unique().tolist() if var_type == 'categorical' and df[col].nunique() < 50 else None
            })
            
        raw_result = {
            'variables': metadata,
            'row_count': len(df),
            'preview': df.head().to_dict(orient='records')
        }
        return DataService.sanitize_for_json(raw_result)

    @staticmethod
    def sanitize_for_json(obj):
        """
        递归地对数据进行清洗，确保其可被 JSON 序列化。
        
        处理逻辑：
        - 将 NaN / Inf 转换为 None。
        - 将 Numpy 数值类型转换为 Python 原生类型。
        """
        if isinstance(obj, dict):
            return {k: DataService.sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DataService.sanitize_for_json(v) for v in obj]
        elif isinstance(obj, float):
            if pd.isna(obj) or math.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, int):
             return int(obj)
        elif hasattr(obj, 'item'): 
            val = obj.item()
            if isinstance(val, float) and (pd.isna(val) or math.isinf(val)):
                return None
            return val
        elif pd.isna(obj): 
            return None
        return obj

    @staticmethod
    def preprocess_for_formula(df):
        """
        Prepare dataframe for Formula-based libraries (statsmodels formulas, lifelines formulas).
        Ensures Object columns are cast to 'category' so the formula engine can auto-encode them.
        """
        df_mod = df.copy()
        for col in df_mod.columns:
            if df_mod[col].dtype == 'object':
                try:
                    df_mod[col] = df_mod[col].astype('float')
                except:
                    df_mod[col] = df_mod[col].astype('category')
        return df_mod

    @staticmethod
    def preprocess_for_matrix(df, features, ref_levels=None):
        """
        Prepare dataframe for Matrix-based libraries.
        Explicitly performs One-Hot Encoding for categorical variables in 'features'.
        Preserves other columns (like target).
        
        Args:
            df (pd.DataFrame): Input dataframe.
            features (list): List of feature names to use.
            ref_levels (dict): Optional. Dict mapping col_name -> ref_category.
                               If provided, the ref_category will be set as the first category 
                               (and thus dropped by drop_first=True to serve as reference).
            
        Returns:
            tuple: (df_encoded, new_features_list)
        """
        df_mod = df.copy()
        
        # Identify categorical cols in FEATURES only
        cat_cols = []
        for col in features:
            if col in df_mod.columns:
                is_cat = df_mod[col].dtype == 'object' or str(df_mod[col].dtype) == 'category'
                # Also treat low cardinality numerics as cat if in ref_levels
                if ref_levels and col in ref_levels:
                    is_cat = True
                    
                if is_cat:
                    cat_cols.append(col)
                    
                    # Handle Reference Level Logic
                    if ref_levels and col in ref_levels:
                        ref_val = ref_levels[col]
                        unique_vals = list(df_mod[col].unique())
                        
                        # Type conversion if needed (e.g. ref is string '0', val is int 0)
                        if df_mod[col].dtype != 'object' and isinstance(ref_val, str):
                            try:
                                ref_val = type(unique_vals[0])(ref_val)
                            except:
                                pass
                                
                        if ref_val in unique_vals:
                            # Move ref_val to front
                            categories = [ref_val] + [x for x in unique_vals if x != ref_val]
                            df_mod[col] = pd.Categorical(df_mod[col], categories=categories, ordered=True)
                        else:
                            # Warn or ignore? For now ignore, let get_dummies handle defaults
                            pass
                
        if not cat_cols:
            return df_mod, features
            
        # One-Hot Encoding
        df_encoded = pd.get_dummies(df_mod, columns=cat_cols, drop_first=True, dtype=int)
        
        # Update feature list
        new_features = [f for f in features if f not in cat_cols]
        
        original_cols = set(df_mod.columns)
        new_cols_set = set(df_encoded.columns)
        
        # Re-calculate generated dummies
        # Note: df_mod might have changed due to Categorical conversion, so we trust new_cols_set
        # Identify new columns that were NOT in original
        
        # Robust way: iterate new columns and check if they start with cat_col + separator
        added_cols = []
        for col in df_encoded.columns:
            if col not in df_mod.columns:
                 added_cols.append(col)
            elif col in cat_cols:
                 # Should not happen as columns=cat_cols drops them
                 pass
        
        new_features.extend(added_cols)
        
        return df_encoded, new_features
