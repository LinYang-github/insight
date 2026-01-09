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
        Impute missing values.
        :param df: pandas DataFrame
        :param strategies: Dict { "col_name": "mean"|"median"|"mode"|"drop" }
        :return: Processed DataFrame
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
        One-Hot Encode nominal variables (get_dummies) to ensure statistical accuracy.
        Drop first level to avoid dummy variable trap (multicollinearity).
        :param df: pandas DataFrame
        :param columns: List of column names to encode
        :return: Processed DataFrame
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
        Save the processed DF as a new Dataset entry.
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
        new_dataset = Dataset(
            project_id=original.project_id,
            filename=new_filename,
            filepath=new_filepath,
            file_size=os.path.getsize(new_filepath),
            uploaded_by=user_id
        )
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
