"""
app.services.data_service.py

负责基础数据操作。
包含稳健的 CSV/Excel 加载、元数据自动提取以及 JSON 序列化前的脱敏处理。
"""
import pandas as pd
import numpy as np
import os
import math
import duckdb

class DataService:
    MAX_FILE_SIZE_MB = 200

    @staticmethod
    def save_dataframe(df, filepath):
        """
        将 DataFrame 保存到文件，根据扩展名处理 DuckDB 或 CSV。
        """
        if filepath.endswith('.duckdb'):
            if os.path.exists(filepath):
                os.remove(filepath)
            con = duckdb.connect(filepath)
            try:
                con.sql("CREATE OR REPLACE TABLE data AS SELECT * FROM df")
            finally:
                con.close()
        else:
            df.to_csv(filepath, index=False)

    @staticmethod
    def ingest_data(raw_filepath, db_filepath):
        """
        将原始文件 (CSV/Excel) 导入持久化的 DuckDB 文件。
        
        参数:
            raw_filepath (str): 临时原始文件路径。
            db_filepath (str): 目标 .duckdb 文件路径。
        """
        if os.path.exists(db_filepath):
            os.remove(db_filepath)

        con = duckdb.connect(db_filepath)
        try:
            if raw_filepath.endswith('.csv'):
                # Use read_csv_auto for robust robust type inference
                # ignore_errors=True skips bad lines
                con.sql(f"CREATE OR REPLACE TABLE data AS SELECT * FROM read_csv_auto('{raw_filepath}', ignore_errors=true)")
            elif raw_filepath.endswith('.xlsx') or raw_filepath.endswith('.xls'):
                # DuckDB Excel support requires extension, fall back to Pandas then insert
                df = pd.read_excel(raw_filepath)
                con.sql("CREATE OR REPLACE TABLE data AS SELECT * FROM df")
            else:
                 raise ValueError("Unsupported format")
        finally:
            con.close()
            # NOTE: We no longer delete the raw file here to prevent accidental data loss
            # during auto-healing or re-ingest operations.

    @staticmethod
    def export_to_csv(db_filepath, output_csv_path):
        """
        将数据从 DuckDB 文件导出到 CSV。
        """
        con = duckdb.connect(db_filepath, read_only=True)
        try:
            # 使用带有 HEADER 的 COPY 语句进行高效导出
            con.sql(f"COPY data TO '{output_csv_path}' (HEADER, DELIMITER ',')")
        finally:
            con.close()

    @staticmethod
    def load_data(filepath, use_chunk=False):
        """
        稳健地加载数据（支持 CSV, Excel）。
        
        针对 CSV 格式，自动尝试 utf-8, gb18030 等多种编码，确保中文无乱码。
        使用 low_memory=False 保证大文件解析的准确性。
        
        Args:
            filepath (str): 文件路径
            use_chunk (bool): 是否使用 chunksize 读取（仅用于元数据预览），返回 iterator
        """
        if filepath.endswith('.duckdb'):
             try:
                 con = duckdb.connect(filepath, read_only=True)
                 try:
                     return con.sql("SELECT * FROM data").df()
                 finally:
                     con.close()
             except (duckdb.SerializationException, duckdb.CatalogException, Exception) as e:
                 # DuckDB version mismatch, missing file, or corruption: Attempt to heal if source exists
                 source_found = False
                 # Remove extension to get base path
                 base_path = filepath.rsplit('.', 1)[0]
                 for ext in ['.csv', '.xlsx', '.xls']:
                     src_path = base_path + ext
                     if os.path.exists(src_path):
                         try:
                             DataService.ingest_data(src_path, filepath)
                             source_found = True
                             break
                         except Exception as ingest_error:
                             # print(f"Ingest failed during healing: {ingest_error}")
                             continue
                 
                 if source_found:
                     con = duckdb.connect(filepath, read_only=True)
                     try:
                         return con.sql("SELECT * FROM data").df()
                     finally:
                         con.close()
                 raise e
 
        # 1. 存在性检查
        if not os.path.exists(filepath):
             raise FileNotFoundError(f"文件未找到: {filepath}")

        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > DataService.MAX_FILE_SIZE_MB:
            raise ValueError(f"文件大小 ({file_size_mb:.1f}MB) 超过限制 ({DataService.MAX_FILE_SIZE_MB}MB)。建议先进行本地预处理。")

        if filepath.endswith('.csv'):
             # 使用编码检测进行稳健解析
            encodings = ['utf-8', 'gb18030', 'latin1']
            df = None
            for encoding in encodings:
                try:
                    # low_memory=False 以避免 DtypeWarning 并确保解析准确
                    if use_chunk:
                         # 仅读取第一个分块以获取元数据
                         return pd.read_csv(filepath, encoding=encoding, chunksize=1000)
                    else:
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
    def load_data_optimized(filepath, columns=None):
        """
        利用 DuckDB 的投影下推（Projection Pushdown）功能优化数据加载。
        仅加载指定的列以最小化内存占用。
        
        参数:
            filepath (str): 文件路径 (.csv, .xlsx, .parquet)。
            columns (list): 要加载的列名列表。如果为 None，则加载所有列。
            
        返回:
            pd.DataFrame: 仅包含所请求列的数据框。
        """
        if not columns:
            return DataService.load_data(filepath)
            
        if filepath.endswith('.duckdb'):
            # 零解析查询（直接内存读取）
            try:
                try:
                    con = duckdb.connect(filepath, read_only=True)
                except (duckdb.SerializationException, duckdb.CatalogException, Exception):
                    # Recovery: Probe for source files
                    source_found = False
                    base_path = filepath.rsplit('.', 1)[0]
                    for ext in ['.csv', '.xlsx', '.xls']:
                        src_path = base_path + ext
                        if os.path.exists(src_path):
                            try:
                                DataService.ingest_data(src_path, filepath)
                                con = duckdb.connect(filepath, read_only=True)
                                source_found = True
                                break
                            except:
                                continue
                    if not source_found:
                        raise

                cols_sql = ", ".join([f'"{c}"' for c in columns])
                df = con.sql(f"SELECT {cols_sql} FROM data").df()
                con.close()
                return df
            except Exception as e:
                # 如果列缺失或数据库损坏，抛出
                raise ValueError(f"DuckDB 查询错误: {e}")
 
        if not filepath.endswith('.csv'):
            # 针对 Excel 回退到 Pandas（DuckDB 的 Excel 支持需要安装扩展）
            df = DataService.load_data(filepath)
            missing = [c for c in columns if c not in df.columns]
            if missing:
                raise ValueError(f"列未找到: {missing}")
            return df[columns]
            
        try:
            # DuckDB SQL 注入保护：内部是否处理了参数化路径？
            # 如果本地路径可信，DuckDB 的 Python API 通常使用 f-string 处理本地路径是安全的。
            # 但列名需要进行清理。
            # 假设列名已经在上游进行了验证/清理，或者足够可信。
            
            # 构建列名字符串
            # 使用双引号引用列名以处理空格/特殊字符
            cols_sql = ", ".join([f'"{c}"' for c in columns])
            
            # 使用 DuckDB 进行查询
            # read_csv_auto 自动处理表头和类型
            query = f"SELECT {cols_sql} FROM read_csv_auto('{filepath}', ignore_errors=true)"
            
            # 执行并获取 Pandas DataFrame
            # 这将触发投影下推：仅从磁盘读取这些特定的列
            df = duckdb.sql(query).df()
            return df
            
        except Exception as e:
            # 如果 DuckDB 失败（例如编码问题，尽管 read_csv_auto 很稳健），则回退到 Pandas
            # print(f"DuckDB failed: {e}, falling back to Pandas")
            df = DataService.load_data(filepath)
            return df[columns]

    @staticmethod
    def get_initial_metadata(filepath):
        """
        读取并生成数据集的初始元数据 (使用 DuckDB 优化大文件读取)。

        Args:
            filepath (str): 数据文件路径 (.duckdb, .csv, .xlsx)。

        Returns:
            dict: 包含变量列表、类型推断、缺失值统计及数据预览的字典。
        """
        preview_data = []
        raw_metadata = []
        row_count = 0
        
        # Use DuckDB for metadata extraction without full load
        con = None
        try:
            # 1. Connect / Create View
            if filepath.endswith('.duckdb'):
                con = duckdb.connect(filepath, read_only=True)
                table_name = "data"
            else:
                con = duckdb.connect(":memory:")
                if filepath.endswith('.csv'):
                    # Create a view directly on the CSV file (zero-copy if possible)
                    con.sql(f"CREATE VIEW data AS SELECT * FROM read_csv_auto('{filepath}', ignore_errors=true)")
                    table_name = "data"
                elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
                    # Excel still needs Pandas load unfortunately, unless we use extensions
                    # Assuming we might have ingested it to DuckDB in upload_data, but if not:
                    df = pd.read_excel(filepath)
                    con.sql("CREATE VIEW data AS SELECT * FROM df")
                    table_name = "data"
                else:
                    raise ValueError("Unsupported format")

            # 2. Get Row Count
            row_count = con.sql(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            # 3. Get Preview (Limit 5)
            # Use fetchdf() to get Pandas DF for easier dict conversion, limits memory usage
            preview_df = con.sql(f"SELECT * FROM {table_name} LIMIT 5").df()
            preview_data = preview_df.replace({np.nan: None}).to_dict(orient='records')
            
            # 4. Get Column Stats using SUMMARIZE
            # SUMMARIZE returns: [column_name, column_type, min, max, approx_unique, avg, std, q25, q50, q75, count, null_percentage]
            # Note: DuckDB SUMMARIZE format might vary by version, let's robustly map
            summary_df = con.sql(f"SUMMARIZE {table_name}").df()
            
            # Map summarize results to our metadata format
            for _, row in summary_df.iterrows():
                col_name = row.get('column_name')
                col_type = row.get('column_type') # DuckDB type (INTEGER, VARCHAR, etc.)
                
                # Missing count: SUMMARIZE gives null_percentage usually string '0.5%'
                # Let's calculate missing count from null_percentage * row_count or 'count'
                # Actually newer DuckDB SUMMARIZE has 'null_percentage'.
                # Let's try to be safe. Some versions return 'count' as non-null count.
                # null_count = row_count - count
                not_null_count = row.get('count', row_count)
                missing_count = row_count - int(not_null_count) if not_null_count is not None else 0
                
                # Unique count: 'approx_unique'
                try:
                    unique_count = int(row.get('approx_unique', 0))
                except:
                    unique_count = 0
                
                # Type Inference
                # Map DuckDB types to our system types (continuous, categorical)
                db_type_str = str(col_type).upper()
                if any(x in db_type_str for x in ['INT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'BIGINT']):
                    var_type = 'continuous'
                else:
                    var_type = 'categorical'
                
                # Heuristics based on stats
                # If continuous but very few uniques (e.g. 0/1), treat as categorical
                if var_type == 'continuous' and unique_count < 10:
                    var_type = 'categorical'
                
                # If categorical but too many uniques, treat as text/id
                if var_type == 'categorical' and unique_count > 50:
                    var_type = 'text/id'
                    
                # Get Categories for small categorical vars
                categories = None
                if var_type == 'categorical' and unique_count < 50:
                    try:
                        # Use DISTINCT query for this specific column
                        cats_df = con.sql(f'SELECT DISTINCT "{col_name}" FROM {table_name} LIMIT 50').df()
                        categories = cats_df.iloc[:,0].dropna().tolist()
                    except:
                        pass

                raw_metadata.append({
                    'name': col_name,
                    'type': var_type,
                    'role': 'covariate',
                    'missing_count': int(missing_count),
                    'unique_count': int(unique_count),
                    'categories': categories
                })

        except Exception as e:
            # Fallback for very old DuckDB or weird errors
            print(f"DuckDB metadata extraction failed: {e}")
            raise e
        finally:
            if con:
                con.close()

        raw_result = {
            'variables': raw_metadata,
            'row_count': int(row_count),
            'preview': preview_data
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
        为基于公式的库 (statsmodels, lifelines) 准备数据框。
        确保将 Object 类型的列转换为 'category'，以便公式引擎能够自动对其进行编码。
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
        为基于矩阵的库准备数据框。
        对 'features' 中的定性变量显式执行独热编码 (One-Hot Encoding)。
        保留其他列（如结局变量）。
        
        参数:
            df (pd.DataFrame): 输入的数据框。
            features (list): 要使用的特征列表。
            ref_levels (dict): 可选。映射列名 -> 参考层级 (ref_category) 的字典。
                               如果提供，参考层级将被设为第一类
                               （因此会被 drop_first=True 丢弃，作为基准参考层）。
            
        返回:
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
                        
                        # 必要时进行类型转换（例如：参考层是字符串 '0'，实际值是整数 0）
                        if df_mod[col].dtype != 'object' and isinstance(ref_val, str):
                            try:
                                ref_val = type(unique_vals[0])(ref_val)
                            except:
                                pass
                                
                        if ref_val in unique_vals:
                            # 将参考层移动到最前面
                            categories = [ref_val] + [x for x in unique_vals if x != ref_val]
                            df_mod[col] = pd.Categorical(df_mod[col], categories=categories, ordered=True)
                        else:
                            # 警告或忽略？目前先忽略，让 get_dummies 处理默认情况
                            pass
                
        if not cat_cols:
            return df_mod, features
            
        # 独热编码 (One-Hot Encoding)
        df_encoded = pd.get_dummies(df_mod, columns=cat_cols, drop_first=True, dtype=int)
        
        # 更新特征列表
        new_features = [f for f in features if f not in cat_cols]
        
        original_cols = set(df_mod.columns)
        new_cols_set = set(df_encoded.columns)
        
        # 重新计算生成的哑变量
        # 注意：df_mod 可能会因为 Categorical 转换而改变，所以我们信任 new_cols_set
        # 识别不在原始列中的新列
        
        # 稳健的方法：迭代新列并检查它们是否以 cat_col + 分隔符开头
        added_cols = []
        for col in df_encoded.columns:
            if col not in df_mod.columns:
                 added_cols.append(col)
            elif col in cat_cols:
                 # Should not happen as columns=cat_cols drops them
                 pass
        
        new_features.extend(added_cols)
        
        return df_encoded, new_features
