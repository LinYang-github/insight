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
            strategies (dict): 策略映射，格式如 { "变量名": "mean"|"median"|"mode"|"drop"|"mice" }。

        Returns:
            pd.DataFrame: 处理后的新 DataFrame。
        """
        # copy to avoid mutating original if needed (though here we want to return new one)
        df = df.copy()

        # 1. 首先处理简单填补和删除
        # (先执行这一步可以确保后续 MICE 预测器在需要时能获得完整的数据)
        mice_cols = []
        
        for col, method in strategies.items():
            if col not in df.columns:
                continue
                
            if method == 'drop':
                df = df.dropna(subset=[col])
            elif method == 'mean':
                if pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].mean()
                    # 如果列是整数类型（包括可为空的 Int64），则转换为 float 以接受均值
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
            elif method == 'mice':
                # 延迟处理 MICE
                if pd.api.types.is_numeric_dtype(df[col]):
                    mice_cols.append(col)
        
        # 2. 处理 MICE 填补
        if mice_cols:
            try:
                from sklearn.experimental import enable_iterative_imputer
                from sklearn.impute import IterativeImputer
                
                # 使用所有数值列作为 MICE 的上下文
                numeric_df = df.select_dtypes(include=[np.number])
                
                # 为了安全起见，MICE 通常需要至少 2 列？
                # 或者如果只有一列则使用单变量填补？ (IterativeImputer 在多变量情况下充当简单回归)
                if numeric_df.shape[1] > 0:
                    # 我们仅需对 mice_cols 中仍包含缺失值的列进行填补
                    # (由于 strategies[col]=='mice'，意味我们要修复它)
                    cols_to_impute = [c for c in mice_cols if df[c].isnull().any()]
                    
                    if cols_to_impute:
                        imputer = IterativeImputer(max_iter=10, random_state=0)
                        # 在所有数值列上进行拟合和转换（实际上会填补所有缺失的数值列）
                        imputed_matrix = imputer.fit_transform(numeric_df)
                        
                        # 转回 DataFrame
                        imputed_df = pd.DataFrame(imputed_matrix, columns=numeric_df.columns, index=numeric_df.index)
                        
                        # 用请求列的填补值更新原始数据框
                        for col in mice_cols:
                            if col in imputed_df.columns:
                                df[col] = imputed_df[col]
            except ImportError:
                 # sklearn 版本问题或未安装时的回退方案
                 print("警告: MICE 需要 sklearn>=0.21。回退至基本的均值填补。")
                 for col in mice_cols:
                     df[col] = df[col].fillna(df[col].mean())
            except Exception as e:
                 print(f"MICE 填补失败: {e}")
                 
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

        # 使用 get_dummies 并设置 drop_first=True 以进行严谨的统计建模
        # 这会将分类 'A','B','C' 转换为 'B','C' (A 作为参考组)
        df = pd.get_dummies(df, columns=valid_cols, drop_first=True)
            
        return df

    @staticmethod
    @staticmethod
    def save_processed_dataset(original_dataset_id, new_df, suffix, user_id, overwrite_id=None, parent_id=None, action_type=None, log=None):
        """
        将处理后的 DataFrame 保存为新的数据集记录并生成物理文件。
        如果提供了 overwrite_id，则更新该数据集而非创建新数据集。
        """
        if overwrite_id:
            # 覆盖现有数据集
            target_dataset = db.session.get(Dataset, overwrite_id)
            if not target_dataset:
                raise ValueError("未找到覆盖目标")
            
            # 使用现有的文件路径
            new_filepath = target_dataset.filepath
            new_dataset = target_dataset
            
            # 保存数据 (覆盖)
            DataService.save_dataframe(new_df, new_filepath)
            
            # 更新元数据
            try:
                meta = DataService.get_initial_metadata(new_filepath)
                new_dataset.meta_data = meta
            except Exception as e:
                pass
            
            db.session.commit()
            return new_dataset
            
        else:
            # 创建新数据集
            original = db.session.get(Dataset, original_dataset_id)
            if not original:
                raise ValueError("未找到原始数据集")
    
            # 创建新文件名
            dir_name = os.path.dirname(original.filepath)
            base_name = os.path.basename(original.filepath)
            name_part, ext = os.path.splitext(base_name)
            
            # 如果原始文件已经是结果文件，也许需要剥离现有后缀？
            # 目前先保持累积后缀逻辑简单。
            new_filename = f"{name_part}_{suffix}{ext}"
            new_filepath = os.path.join(dir_name, new_filename)
            
            # 保存数据 (DuckDB 或 CSV)
            DataService.save_dataframe(new_df, new_filepath)
            
            # 创建数据库条目
            new_dataset = Dataset(
                project_id=original.project_id,
                name=new_filename,
                filepath=new_filepath,
                parent_id=parent_id if parent_id else original.id,
                action_type=action_type,
                action_log=json.dumps(log) if log else None
            )
            # 生成元数据
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
                race_col = params.get('race') # 可选, 1=Black, 0=Other
                
                if not (scr_col and age_col and sex_col):
                     raise ValueError("缺少必要列：scr, age, sex")
 
                def calc_2009(row):
                    scr = pd.to_numeric(row[scr_col], errors='coerce')
                    age = pd.to_numeric(row[age_col], errors='coerce')
                    sex = str(row[sex_col]).lower() # female/male 或 0/1 (需统一规范)
                    # 性别简单启发式判定: 'f', 'female', '0' -> Female
                    is_female = sex in ['f', 'female', '0', 'woman']
                    is_black = False
                    if race_col and race_col in row:
                        r = str(row[race_col]).lower()
                        is_black = r in ['black', '1', 'african']

                    if pd.isna(scr) or pd.isna(age): return np.nan
                    
                    # Kappa, Alpha
                    k = 0.7 if is_female else 0.9
                    a = -0.329 if is_female else -0.411
                    
                    # 种族系数
                    race_factor = 1.159 if is_black else 1.0
                    sex_factor = 1.018 if is_female else 1.0 
                    # 注：单方程形式：
                    # eGFR = 141 * min(Scr/k, 1)^a * max(Scr/k, 1)^-1.209 * 0.993^Age * sex_factor * race_factor
                    
                    # 我们使用显式的拆解计算
                    return 141 * (min(scr/k, 1)**a) * (max(scr/k, 1)**-1.209) * (0.993**age) * sex_factor * race_factor

                df['eGFR_CKDEPI_2009'] = df.apply(calc_2009, axis=1)

            elif type == 'egfr_ckdepi2021':
                # CKD-EPI 2021 (不含种族因素)
                # 参数: scr, age, sex
                scr_col = params.get('scr')
                age_col = params.get('age')
                sex_col = params.get('sex')
                
                if not (scr_col and age_col and sex_col):
                     raise ValueError("缺少必要列：scr, age, sex")

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
                     raise ValueError("缺少必要列")

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
                # Bedside Schwartz 法 (儿童)
                # eGFR = 0.413 * (身高 cm / Scr )
                scr_col = params.get('scr')
                height_col = params.get('height')
                
                if not (scr_col and height_col):
                     raise ValueError("缺少必要列：scr, height")
                
                def calc_schwartz(row):
                    scr = pd.to_numeric(row[scr_col], errors='coerce')
                    h = pd.to_numeric(row[height_col], errors='coerce') # cm
                    if pd.isna(scr) or pd.isna(h): return np.nan
                    return 0.413 * (h / scr)
                
                df['eGFR_Schwartz'] = df.apply(calc_schwartz, axis=1)

        except Exception as e:
            raise ValueError(f"变量衍生失败: {str(e)}")

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
        acr_col = params.get('acr') # ACR (mg/g) 或 PCR
        
        if not egfr_col:
            raise ValueError("eGFR 列是必需的")
            
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
        
        # 2. A 分期 (如果提供了 ACR)
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
            
            # 3. 风险分层 (KDIGO 热图)
            # 低风险 (绿色), 中度风险 (黄色), 高风险 (橙色), 极高风险 (红色)
            def calc_risk(row):
                g = row.get('CKD_G_Stage')
                a = row.get('CKD_A_Stage')
                if pd.isna(g) or pd.isna(a): return np.nan
                
                # KDIGO 2012 热图逻辑
                #      A1      A2      A3
                # G1   低风险  中偏高  高风险
                # G2   低风险  中偏高  高风险
                # G3a  中偏高  高风险  极高
                # G3b  高风险  极高    极高
                # G4   极高    极高    极高
                # G5   极高    极高    极高
                
                risk_map = {
                    ('G1', 'A1'): '低风险 (Low Risk)',   ('G1', 'A2'): '中度风险 (Moderate Risk)', ('G1', 'A3'): '高风险 (High Risk)',
                    ('G2', 'A1'): '低风险 (Low Risk)',   ('G2', 'A2'): '中度风险 (Moderate Risk)', ('G2', 'A3'): '高风险 (High Risk)',
                    ('G3a', 'A1'): '中度风险 (Moderate Risk)', ('G3a', 'A2'): '高风险 (High Risk)',   ('G3a', 'A3'): '极高风险 (Very High Risk)',
                    ('G3b', 'A1'): '高风险 (High Risk)',     ('G3b', 'A2'): '极高风险 (Very High Risk)', ('G3b', 'A3'): '极高风险 (Very High Risk)',
                    ('G4', 'A1'): '极高风险 (Very High Risk)', ('G4', 'A2'): '极高风险 (Very High Risk)', ('G4', 'A3'): '极高风险 (Very High Risk)',
                    ('G5', 'A1'): '极高风险 (Very High Risk)', ('G5', 'A2'): '极高风险 (Very High Risk)', ('G5', 'A3'): '极高风险 (Very High Risk)',
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
        计算线性斜率 (OLS Slope)。
        模型: Value ~ Intercept + Slope * Time
        
        Args:
            df (pd.DataFrame): 长格式数据。
            id_col, time_col, value_col: 列名。
            
        Returns:
            pd.DataFrame: [id_col, 'Slope', 'Intercept', 'R2', 'N_Points']
        """
        from scipy import stats
        
        results = []
        # Group by patient
        grouped = df.groupby(id_col)
        
        for pid, group in grouped:
            # 至少需要 2 个点
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
        # 稍微重复了 DataService 的逻辑，但为了安全导入保持独立
        # 或更好：如果可能，使用 DataService，但避免循环导入更重要。
        # 目前暂时复制稳健读取逻辑 (KISS)
        encodings = ['utf-8', 'gb18030', 'latin1']
        for enc in encodings:
            try:
                return pd.read_csv(filepath, encoding=enc, low_memory=False)
            except:
                continue
        return None
