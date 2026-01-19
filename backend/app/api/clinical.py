from flask import Blueprint, request, jsonify
from app.services.preprocessing_service import PreprocessingService
from app.services.data_service import DataService
from app.models.dataset import Dataset
from app import db
from app.api.middleware import token_required
import pandas as pd
import traceback

clinical_bp = Blueprint('clinical', __name__)

@clinical_bp.route('/derive-egfr', methods=['POST'])
@token_required
def derive_egfr(current_user):
    """
    计算 eGFR 衍生变量。
    Request Body:
    {
        "dataset_id": 1,
        "type": "egfr_ckdepi2009",
        "params": { "scr": "Creatinine", "age": "Age", ... }
    }
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    formula_type = data.get('type')
    params = data.get('params')
    save_mode = data.get('save_mode', 'new') # new, overwrite
    
    if not all([dataset_id, formula_type, params]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset or dataset.project.user_id != current_user.id:
        return jsonify({'message': 'Dataset not found or unauthorized'}), 404
        
    # Load data
    df = DataService.load_data(dataset.filepath)
    if df is None:
        return jsonify({'message': 'Failed to load dataset'}), 500
        
    # Derive
    new_df = PreprocessingService.derive_variable(df, formula_type, params)
    
    # Save
    suffix = formula_type.replace('egfr_', 'Egfr')
    
    overwrite_id = dataset.id if save_mode == 'overwrite' else None
    
    new_dataset = PreprocessingService.save_processed_dataset(dataset.id, new_df, suffix, current_user.id, overwrite_id=overwrite_id)
    
    return jsonify({
        'message': 'Derived variable created successfully',
        'new_dataset': {
            'id': new_dataset.id,
            'name': new_dataset.name,
            'metadata': new_dataset.meta_data
        }
    }), 200

@clinical_bp.route('/stage-ckd', methods=['POST'])
@token_required
def stage_ckd(current_user):
    """
    CKD 自动分期 (G-stage, A-stage, Risk)。
    Request Body:
    {
        "dataset_id": 1,
        "params": { "egfr": "eGFR_CKDEPI_2021", "acr": "ACR" }
    }
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    params = data.get('params')
    save_mode = data.get('save_mode', 'new')
    
    if not all([dataset_id, params]) or not params.get('egfr'):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset or dataset.project.user_id != current_user.id:
        return jsonify({'message': 'Dataset not found or unauthorized'}), 404
        
    df = DataService.load_data(dataset.filepath)
    new_df = PreprocessingService.derive_ckd_staging(df, params)
    
    overwrite_id = dataset.id if save_mode == 'overwrite' else None
    
    new_dataset = PreprocessingService.save_processed_dataset(dataset.id, new_df, 'Staged', current_user.id, overwrite_id=overwrite_id)
    
    return jsonify({
        'message': 'CKD Staging complete',
        'new_dataset': {
            'id': new_dataset.id,
            'name': new_dataset.name,
            'metadata': new_dataset.meta_data
        }
    }), 200

@clinical_bp.route('/melt', methods=['POST'])
@token_required
def melt_data(current_user):
    """
    长宽表转换 (Wide to Long).
    Request Body:
    {
        "dataset_id": 1,
        "id_col": "PatientID",
        "time_mapping": { "eGFR_0m": 0, "eGFR_6m": 6, "eGFR_12m": 12 },
        "value_name": "eGFR"
    }
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    id_col = data.get('id_col')
    time_mapping = data.get('time_mapping')
    value_name = data.get('value_name', 'Value')
    save_mode = data.get('save_mode', 'new')
    
    if not all([dataset_id, id_col, time_mapping]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset or dataset.project.user_id != current_user.id:
        return jsonify({'message': 'Dataset not found or unauthorized'}), 404
        
    df = DataService.load_data(dataset.filepath)
    new_df = PreprocessingService.melt_to_long(df, id_col, time_mapping, value_name)
    
    overwrite_id = dataset.id if save_mode == 'overwrite' else None
    
    new_dataset = PreprocessingService.save_processed_dataset(dataset.id, new_df, 'Long', current_user.id, overwrite_id=overwrite_id)
    
    return jsonify({
        'message': 'Data melted successfully',
        'new_dataset': {
            'id': new_dataset.id,
            'name': new_dataset.name,
            'metadata': new_dataset.meta_data
        }
    }), 200

@clinical_bp.route('/calculate-slope', methods=['POST'])
@token_required
def calculate_slope(current_user):
    """
    计算 eGFR 斜率 (Longitudinal).
    Request Body:
    {
        "dataset_id": 1,
        "id_col": "PatientID",
        "time_col": "Time",
        "value_col": "eGFR"
    }
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    id_col = data.get('id_col')
    time_col = data.get('time_col')
    value_col = data.get('value_col')
    save_mode = data.get('save_mode', 'new')
    
    if not all([dataset_id, id_col, time_col, value_col]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = db.session.get(Dataset, dataset_id)
    if not dataset or dataset.project.user_id != current_user.id:
        return jsonify({'message': 'Dataset not found or unauthorized'}), 404
        
    df = DataService.load_data(dataset.filepath)
    new_df = PreprocessingService.calculate_slope(df, id_col, time_col, value_col)
    
    # Merge slope back to original unique patient list?
    # Usually user wants a patient-level summary table.
    # But if the input is Long, we get a summary table with 1 row per patient.
    # This is perfect for subsequent analysis.
    
    overwrite_id = dataset.id if save_mode == 'overwrite' else None
    new_dataset = PreprocessingService.save_processed_dataset(dataset.id, new_df, 'Slopes', current_user.id, overwrite_id=overwrite_id)
    
    return jsonify({
        'message': 'Slope calculation complete',
        'new_dataset': {
            'id': new_dataset.id,
            'name': new_dataset.name,
            'metadata': new_dataset.meta_data
        }
    }), 200
@clinical_bp.route('/ai-suggest-roles', methods=['POST'])
@token_required
def ai_suggest_roles(current_user):
    """
    AI 智能角色推荐 (Clinical).
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    tool_type = data.get('tool_type') # 'egfr', 'staging', 'slope'
    
    if not dataset_id or not tool_type:
        return jsonify({'message': 'Missing parameters'}), 400

    dataset = db.session.get(Dataset, dataset_id)
    if not dataset or dataset.project.user_id != current_user.id:
        return jsonify({'message': 'Dataset not found'}), 404

    # Get AI Config
    from app.api.projects import get_ai_config
    api_key, api_base, api_model = get_ai_config(current_user)
    
    if not api_key:
        return jsonify({'message': '未配置 AI API Key'}), 400

    from app.services.ai_service import AIService
    try:
        # Map tool_type to AIService model_type
        # tool_type from frontend: 'egfr', 'staging', 'slope'
        model_type_map = {
            'egfr': 'clinical_egfr',
            'staging': 'clinical_staging',
            'slope': 'clinical_slope'
        }
        
        analysis_type = model_type_map.get(tool_type, 'clinical_egfr')
        
        # Get variables
        variables = dataset.meta_data.get('variables', [])
        
        suggestion = AIService.suggest_variable_roles(
            analysis_type, variables, api_key, api_base, api_model
        )
        return jsonify(suggestion), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
