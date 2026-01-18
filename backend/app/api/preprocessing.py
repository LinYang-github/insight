"""
app.api.preprocessing.py

数据预处理相关路由。
提供缺失值填补 (Imputation) 和分类变量因子化 (Encoding) 的接口。
"""
from flask import Blueprint, jsonify, request
from app.services.preprocessing_service import PreprocessingService
from app.models.dataset import Dataset
from app.api.projects import token_required

preprocessing_bp = Blueprint('preprocessing', __name__)

@preprocessing_bp.route('/impute', methods=['POST'])
@token_required
def impute(current_user):
    """
    缺失值填补接口。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    strategies = data.get('strategies') # {col: method}
    
    if not dataset_id or not strategies:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    # Check permissions (omitted for MVP speed)
    
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    new_df = PreprocessingService.impute_data(df, strategies)
    new_dataset = PreprocessingService.save_processed_dataset(
        dataset_id, 
        new_df, 
        'imputed', 
        current_user.id,
        parent_id=dataset_id,
        action_type='impute',
        log=strategies
    )
    return jsonify({'message': 'Imputation successful', 'new_dataset_id': new_dataset.id}), 200

@preprocessing_bp.route('/encode', methods=['POST'])
@token_required
def encode(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    columns = data.get('columns') # [col1, col2]
    
    if not dataset_id or not columns:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    from app.services.data_service import DataService
    df = DataService.load_data(dataset.filepath)
    new_df = PreprocessingService.encode_data(df, columns)
    new_dataset = PreprocessingService.save_processed_dataset(
        dataset_id, 
        new_df, 
        'encoded', 
        current_user.id,
        parent_id=dataset_id,
        action_type='encode',
        log={'columns': columns}
    )
    return jsonify({'message': 'Encoding successful', 'new_dataset_id': new_dataset.id}), 200

@preprocessing_bp.route('/ai-suggest-strategies', methods=['POST'])
@token_required
def ai_suggest_strategies(current_user):
    """
    使用 AI 推荐缺失值处理策略。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    if not dataset_id:
        return jsonify({'message': 'Missing dataset_id'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    metadata = dataset.meta_data
    if not metadata:
        return jsonify({'message': 'No metadata found for dataset'}), 400
        
    user_settings = current_user.settings or {}
    api_key = user_settings.get('llm_key')
    api_base = user_settings.get('llm_api_base') or "https://api.openai.com/v1"
    api_model = user_settings.get('llm_model') or "gpt-4o"
    
    if not api_key:
        return jsonify({'message': '未配置 AI API Key，请前往“系统设置 -> AI 配置”中配置。'}), 400
        
    from app.services.ai_service import AIService
    try:
        recommendation = AIService.suggest_cleaning_strategies(
            metadata['variables'], 
            metadata['row_count'], 
            api_key, 
            api_base, 
            model=api_model
        )
        return jsonify(recommendation), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
