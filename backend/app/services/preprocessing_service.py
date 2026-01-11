"""
app.services.preprocessing_service.py

数据预处理服务。
提供缺失值填补 (Imputation) 和分类变量编码 (Encoding) 功能。
"""
import pandas as pd
import numpy as np
from app.services.data_service import DataService
from app.models.dataset import Dataset
from app import db
import os
import json

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
                    # If column is integer (including nullable Int64), cast to float to accept mean (likely float)
                    if pd.api.types.is_integer_dtype(df[col]):
                        df[col] = df[col].astype(float)
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
    @staticmethod
    def save_processed_dataset(original_dataset_id, new_df, suffix, user_id, overwrite_id=None, parent_id=None, action_type=None, log=None):
        """
        将处理后的 DataFrame 保存为新的数据集记录并生成物理文件。
        If overwrite_id is provided, updates that dataset instead of creating new.
        """
        if overwrite_id:
            # Overwrite existing dataset
            target_dataset = db.session.get(Dataset, overwrite_id)
            if not target_dataset:
                raise ValueError("Overwrite target not found")
            
            # Use existing filepath
            new_filepath = target_dataset.filepath
            new_dataset = target_dataset
            
            # Save Data (Overwrite)
            DataService.save_dataframe(new_df, new_filepath)
            
            # Update Metadata
            try:
                meta = DataService.get_initial_metadata(new_filepath)
                new_dataset.meta_data = meta
            except Exception as e:
                pass
            
            db.session.commit()
            return new_dataset
            
        else:
            # Create NEW dataset
            original = db.session.get(Dataset, original_dataset_id)
            if not original:
                raise ValueError("Original dataset not found")
    
            # Create new filename
            dir_name = os.path.dirname(original.filepath)
            base_name = os.path.basename(original.filepath)
            name_part, ext = os.path.splitext(base_name)
            
            # If original is already a Result file, maybe strip existing suffix?
            # Ideally we keep accumulating suffix logic simple for now.
            new_filename = f"{name_part}_{suffix}{ext}"
            new_filepath = os.path.join(dir_name, new_filename)
            
            # Save Data (DuckDB or CSV)
            DataService.save_dataframe(new_df, new_filepath)
            
            # Create DB entry
            new_dataset = Dataset(
                project_id=original.project_id,
                name=new_filename,
                filepath=new_filepath,
                parent_id=parent_id if parent_id else original.id,
                action_type=action_type,
                action_log=json.dumps(log) if log else None
            )
            # Generate metadata
            try:
                meta = DataService.get_initial_metadata(new_filepath)
                new_dataset.meta_data = meta
            except Exception as e:
                pass 
                
            db.session.add(new_dataset)
            db.session.commit()
            
            return new_dataset

    @staticmethod
    def derive_variable(df, type, params):
        """
        生成衍生变量。
        
        Args:
            df (pd.DataFrame): 原始数据
            type (str): 计算类型，目前的 'egfr_ckdepi2009', 'egfr_ckdepi2021', 'egfr_mdrd', 'egfr_schwartz'
            params (dict): 参数映射，格式 { "scr": "Creatinine", "age": "Age", ... }
            
        Returns:
            pd.DataFrame: 除带新变量的数据集
        """
        df = df.copy()
        
        try:
            if type == 'egfr_ckdepi2009':
                # CKD-EPI 2009 (Scr in mg/dL)
                # Params: scr, age, sex, race
                scr_col = params.get('scr')
                age_col = params.get('age')
                sex_col = params.get('sex')
                race_col = params.get('race') # Optional, 1=Black, 0=Other
                
                if not (scr_col and age_col and sex_col):
                     raise ValueError("Missing required columns: scr, age, sex")

                def calc_2009(row):
                    scr = pd.to_numeric(row[scr_col], errors='coerce')
                    age = pd.to_numeric(row[age_col], errors='coerce')
                    sex = str(row[sex_col]).lower() # female/male or 0/1 (need standard)
                    # Simple heuristic for Sex: 'f', 'female', '0' -> Female
                    is_female = sex in ['f', 'female', '0', 'woman']
                    is_black = False
                    if race_col and race_col in row:
                        r = str(row[race_col]).lower()
                        is_black = r in ['black', '1', 'african']

                    if pd.isna(scr) or pd.isna(age): return np.nan
                    
                    # Kappa, Alpha
                    k = 0.7 if is_female else 0.9
                    a = -0.329 if is_female else -0.411
                    
                    # Race factor
                    race_factor = 1.159 if is_black else 1.0
                    sex_factor = 1.018 if is_female else 1.0 
                    # Note: The single equation form:
                    # eGFR = 141 * min(Scr/k, 1)^a * max(Scr/k, 1)^-1.209 * 0.993^Age * sex_factor * race_factor
                    
                    # Let's use the explicit breakdown
                    return 141 * (min(scr/k, 1)**a) * (max(scr/k, 1)**-1.209) * (0.993**age) * sex_factor * race_factor

                df['eGFR_CKDEPI_2009'] = df.apply(calc_2009, axis=1)

            elif type == 'egfr_ckdepi2021':
                # CKD-EPI 2021 (Refit without Race)
                # Params: scr, age, sex
                scr_col = params.get('scr')
                age_col = params.get('age')
                sex_col = params.get('sex')
                
                if not (scr_col and age_col and sex_col):
                     raise ValueError("Missing required columns: scr, age, sex")

                def calc_2021(row):
                    scr = pd.to_numeric(row[scr_col], errors='coerce')
                    age = pd.to_numeric(row[age_col], errors='coerce')
                    sex = str(row[sex_col]).lower()
                    is_female = sex in ['f', 'female', '0', 'woman']
                    
                    if pd.isna(scr) or pd.isna(age): return np.nan

                    k = 0.7 if is_female else 0.9
                    a = -0.241 if is_female else -0.302
                    sex_factor = 1.012 if is_female else 1.0
                    
                    # eGFR = 142 * min(Scr/k, 1)^a * max(Scr/k, 1)^-1.200 * 0.9938^Age * sex_factor
                    return 142 * (min(scr/k, 1)**a) * (max(scr/k, 1)**-1.200) * (0.9938**age) * sex_factor

                df['eGFR_CKDEPI_2021'] = df.apply(calc_2021, axis=1)

            elif type == 'egfr_mdrd':
                # MDRD
                # eGFR = 175 * Scr^-1.154 * Age^-0.203 * 0.742 (if female) * 1.212 (if black)
                scr_col = params.get('scr')
                age_col = params.get('age')
                sex_col = params.get('sex')
                race_col = params.get('race')

                if not (scr_col and age_col and sex_col):
                     raise ValueError("Missing required columns")

                def calc_mdrd(row):
                    scr = pd.to_numeric(row[scr_col], errors='coerce')
                    age = pd.to_numeric(row[age_col], errors='coerce')
                    sex = str(row[sex_col]).lower()
                    is_female = sex in ['f', 'female', '0', 'woman']
                    is_black = False
                    if race_col and race_col in row:
                        r = str(row[race_col]).lower()
                        is_black = r in ['black', '1', 'african']

                    if pd.isna(scr) or pd.isna(age): return np.nan
                    
                    val = 175 * (scr**-1.154) * (age**-0.203)
                    if is_female: val *= 0.742
                    if is_black: val *= 1.212
                    return val

                df['eGFR_MDRD'] = df.apply(calc_mdrd, axis=1)

            elif type == 'egfr_schwartz':
                # Bedside Schwartz (Children)
                # eGFR = 0.413 * (Height cm / Scr )
                scr_col = params.get('scr')
                height_col = params.get('height')
                
                if not (scr_col and height_col):
                     raise ValueError("Missing columns: scr, height")
                
                def calc_schwartz(row):
                    scr = pd.to_numeric(row[scr_col], errors='coerce')
                    h = pd.to_numeric(row[height_col], errors='coerce') # cm
                    if pd.isna(scr) or pd.isna(h): return np.nan
                    return 0.413 * (h / scr)
                
                df['eGFR_Schwartz'] = df.apply(calc_schwartz, axis=1)

        except Exception as e:
            raise ValueError(f"Derivation failed: {str(e)}")

        return df


    @staticmethod
    def derive_ckd_staging(df, params):
        """
        生成 CKD 分期变量 (KDIGO 指南).
        
        Args:
           df (pd.DataFrame): Data
           params (dict): { "egfr": "eGFR_col", "acr": "ACR_col" }
           
        Returns:
            pd.DataFrame: With new columns CKD_G_Stage, CKD_A_Stage, CKD_Risk_Level
        """
        df = df.copy()
        
        egfr_col = params.get('egfr')
        acr_col = params.get('acr') # ACR (mg/g) or PCR
        
        if not egfr_col:
            raise ValueError("eGFR column is required")
            
        # 1. G-Stage
        def calc_g_stage(val):
            try:
                v = float(val)
                if pd.isna(v): return np.nan
                if v >= 90: return 'G1'
                if v >= 60: return 'G2'
                if v >= 45: return 'G3a'
                if v >= 30: return 'G3b'
                if v >= 15: return 'G4'
                return 'G5'
            except:
                return np.nan
        
        df['CKD_G_Stage'] = df[egfr_col].apply(calc_g_stage)
        
        # 2. A-Stage (Optional if ACR not provided)
        if acr_col:
            def calc_a_stage(val):
                try:
                    v = float(val)
                    if pd.isna(v): return np.nan
                    if v < 30: return 'A1'
                    if v <= 300: return 'A2'
                    return 'A3'
                except:
                    return np.nan
            df['CKD_A_Stage'] = df[acr_col].apply(calc_a_stage)
            
            # 3. Risk Stratification (KDIGO Heatmap)
            # Low (Green), Moderate (Yellow), High (Orange), Very High (Red)
            def calc_risk(row):
                g = row.get('CKD_G_Stage')
                a = row.get('CKD_A_Stage')
                if pd.isna(g) or pd.isna(a): return np.nan
                
                # KDIGO 2012 Heatmap Logic
                #      A1      A2      A3
                # G1   Low     Mod     High
                # G2   Low     Mod     High
                # G3a  Mod     High    V.High
                # G3b  High    V.High  V.High
                # G4   V.High  V.High  V.High
                # G5   V.High  V.High  V.High
                
                risk_map = {
                    ('G1', 'A1'): 'Low Risk',   ('G1', 'A2'): 'Moderate Risk', ('G1', 'A3'): 'High Risk',
                    ('G2', 'A1'): 'Low Risk',   ('G2', 'A2'): 'Moderate Risk', ('G2', 'A3'): 'High Risk',
                    ('G3a', 'A1'): 'Moderate Risk', ('G3a', 'A2'): 'High Risk',   ('G3a', 'A3'): 'Very High Risk',
                    ('G3b', 'A1'): 'High Risk',     ('G3b', 'A2'): 'Very High Risk', ('G3b', 'A3'): 'Very High Risk',
                    ('G4', 'A1'): 'Very High Risk', ('G4', 'A2'): 'Very High Risk', ('G4', 'A3'): 'Very High Risk',
                    ('G5', 'A1'): 'Very High Risk', ('G5', 'A2'): 'Very High Risk', ('G5', 'A3'): 'Very High Risk',
                }
                
                return risk_map.get((g, a), np.nan)
            
            df['CKD_Risk_Level'] = df.apply(calc_risk, axis=1)
            
        return df

        return df

    @staticmethod
    def melt_to_long(df, id_col, time_mapping, value_name='Value'):
        """
        宽表转长表。
        Args:
            df (pd.DataFrame): Wide format.
            id_col (str): Patient ID.
            time_mapping (dict): { "col_name_t1": 0, "col_name_t2": 6, ... } -> Maps column to time value (months/years).
            value_name (str): Name for value column.
        Returns:
            pd.DataFrame: Long format [id_col, 'Time', value_name]
        """
        df = df.copy()
        melted_rows = []
        
        for _, row in df.iterrows():
            pid = row[id_col]
            for col, time_val in time_mapping.items():
                if col in row and pd.notna(row[col]):
                    melted_rows.append({
                        id_col: pid,
                        'Time': time_val,
                        value_name: row[col]
                    })
        
        return pd.DataFrame(melted_rows)

    @staticmethod
    def calculate_slope(df, id_col, time_col, value_col):
        """
        计算线性斜率 (OLS Slope).
        model: Value ~ Intercept + Slope * Time
        
        Args:
            df (pd.DataFrame): Long format data.
            id_col, time_col, value_col: column names.
            
        Returns:
            pd.DataFrame: [id_col, 'Slope', 'Intercept', 'R2', 'N_Points']
        """
        from scipy import stats
        
        results = []
        # Group by patient
        grouped = df.groupby(id_col)
        
        for pid, group in grouped:
            # Need at least 2 points
            clean_group = group.dropna(subset=[time_col, value_col])
            if len(clean_group) < 2:
                results.append({
                    id_col: pid, 'Slope': np.nan, 'Intercept': np.nan, 'R2': np.nan, 'N_Points': len(clean_group)
                })
                continue
                
            x = pd.to_numeric(clean_group[time_col])
            y = pd.to_numeric(clean_group[value_col])
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            results.append({
                id_col: pid,
                'Slope': slope,
                'Intercept': intercept,
                'R2': r_value**2,
                'N_Points': len(clean_group)
            })
            
        return pd.DataFrame(results)

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
