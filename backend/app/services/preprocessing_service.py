"""
app.services.preprocessing_service.py

数据预处理服务。
提供缺失值填补 (Imputation) 和分类变量编码 (Encoding) 功能。
"""
import pandas as pd
import numpy as np
from app.services.data_service import DataService
from app.models.dataset import Dataset
from app.api.auth import db
import os

class PreprocessingService:
    @staticmethod
    def impute_data(df, strategies):
        """
        根据指定策略填补缺失值。

        Args:
            df (pd.DataFrame): 原始数据集。
            strategies (dict): 策略映射，格式如 { "变量名": "mean"|"median"|"mode"|"drop" }。

        Returns:
            pd.DataFrame: 处理后的新 DataFrame。
        """
        # copy to avoid mutating original if needed (though here we want to return new one)
        df = df.copy()

        for col, method in strategies.items():
            if col not in df.columns:
                continue
                
            if method == 'drop':
                df = df.dropna(subset=[col])
            elif method == 'mean':
                if pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].mean()
                    df[col] = df[col].fillna(val)
            elif method == 'median':
                if pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].median()
                    df[col] = df[col].fillna(val)
            elif method == 'mode':
                if not df[col].mode().empty:
                    val = df[col].mode()[0]
                    df[col] = df[col].fillna(val)
                    
        return df

    @staticmethod
    def encode_data(df, columns):
        """
        对分类变量进行独热编码 (One-Hot Encoding/Dummy Encoding)。
        
        通过 pd.get_dummies 实现。
        NOTE: 设置 drop_first=True 以避免“虚拟变量陷阱” (Dummy Variable Trap)，即多重共线性问题，这对于线性/逻辑回归至关重要。

        Args:
            df (pd.DataFrame): 原始数据。
                columns (list): 需要编码的列名列表。

        Returns:
            pd.DataFrame: 编码后的数据集。
        """
        df = df.copy()
        
        valid_cols = [c for c in columns if c in df.columns]
        if not valid_cols:
            return df

        # Use get_dummies with drop_first=True for rigorous statistical modeling
        # This converts nominal 'A','B','C' -> 'B','C' (A is reference)
        df = pd.get_dummies(df, columns=valid_cols, drop_first=True)
            
        return df

    @staticmethod
    def save_processed_dataset(original_dataset_id, new_df, suffix, user_id):
        """
        将处理后的 DataFrame 保存为新的数据集记录并生成物理文件。
        """
        original = Dataset.query.get(original_dataset_id)
        if not original:
            raise ValueError("Original dataset not found")

        # Create new filename
        dir_name = os.path.dirname(original.filepath)
        base_name = os.path.basename(original.filepath)
        name_part, ext = os.path.splitext(base_name)
        new_filename = f"{name_part}_{suffix}{ext}"
        new_filepath = os.path.join(dir_name, new_filename)
        
        # Save CSV
        new_df.to_csv(new_filepath, index=False)
        
        # Create DB entry
        # Create DB entry
        new_dataset = Dataset(
            project_id=original.project_id,
            name=new_filename,
            filepath=new_filepath
        )
        # Generate metadata
        try:
            from app.services.data_service import DataService
            meta = DataService.get_initial_metadata(new_filepath)
            new_dataset.meta_data = meta
        except Exception as e:
            # print(f"Meta gen failed: {e}")
            pass 
        db.session.add(new_dataset)
        db.session.commit()
        
        return new_dataset

    @staticmethod
    def _read_robust(filepath):
        # Reinventing the wheel slightly vs DataService, but keeping isolated for safe import
        # Or better: use DataService if possible, but avoiding circular imports is good.
        # Let's simple duplicate robust read logic for now (KISS)
        encodings = ['utf-8', 'gb18030', 'latin1']
        for enc in encodings:
            try:
                return pd.read_csv(filepath, encoding=enc, low_memory=False)
            except:
                continue
        return None
