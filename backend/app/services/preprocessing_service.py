import pandas as pd
import numpy as np
from app.services.data_service import DataService
from app.models.dataset import Dataset
from app.api.auth import db
import os

class PreprocessingService:
    @staticmethod
    def impute_data(filepath, strategies):
        """
        Impute missing values.
        :param filepath: Path to CSV
        :param strategies: Dict { "col_name": "mean"|"median"|"mode"|"drop" }
        :return: Processed DataFrame
        """
        # Robust read
        df = PreprocessingService._read_robust(filepath)
        if df is None:
            raise ValueError("Failed to read file")

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
    def encode_data(filepath, columns):
        """
        Factorize (Label Encode) variables.
        :param filepath: Path to CSV
        :param columns: List of column names to encode
        :return: Processed DataFrame
        """
        df = PreprocessingService._read_robust(filepath)
        if df is None:
            raise ValueError("Failed to read file")

        for col in columns:
            if col not in df.columns:
                continue
            # Use pandas factorize (returns codes, uniques)
            codes, uniques = pd.factorize(df[col])
            # Replace with codes
            df[col] = codes
            
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
