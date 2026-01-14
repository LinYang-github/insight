"""
app.api.modeling.py

统计建模相关路由。
提供模型训练、结果导出等 API 支持。
"""
from flask import Blueprint, request, jsonify
from app.api.projects import token_required
from app.services.modeling_service import ModelingService
from app.models.project import Project
from app.models.dataset import Dataset
import pandas as pd
import os # missing import fixed
from app.services.data_service import DataService # Moved import to top for consistency

modeling_bp = Blueprint('modeling', __name__)

@modeling_bp.route('/run', methods=['POST'])
@token_required
def run_model(current_user):
    """
    运行统计模型。
    
    接收数据集、结局变量 (Outcome) 和协变量 (Covariates)，执行指定的统计建模任务。
    """
    data = request.get_json()
    
    project_id = data.get('project_id')
    dataset_id = data.get('dataset_id')
    
    # Extract model parameters with defaults
    target = data.get('target')
    features = data.get('features', [])
    model_type = data.get('model_type', 'linear') # linear, logistic, cox
    params = data.get('params', {}) # For future use, e.g., specific model parameters
    
    # Validation
    if not all([project_id, dataset_id, model_type, target, features is not None]): # features can be empty list
        return jsonify({'message': 'Missing required parameters (project_id, dataset_id, model_type, target, features)'}), 400
        
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
        
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.project_id != project.id:
        return jsonify({'message': 'Dataset does not belong to project'}), 400
        
    # Use robust loading from DataService
    # Optimization
    
    # 1. Handle Feature Objects (if frontend sends dicts)
    feature_names = []
    if features:
        for f in features:
            if isinstance(f, dict):
                # Try common keys
                feature_names.append(f.get('name') or f.get('value')) 
            else:
                feature_names.append(str(f))
    features = feature_names

    # 2. Handle Target (String vs Dict for Cox)
    required_cols = []
    if isinstance(target, dict):
        required_cols.extend(target.values())
    else:
        required_cols.append(target)
        
    required_cols.extend(features)
    
    # Dedup strings
    required = list(set(required_cols))
    
    df = DataService.load_data_optimized(dataset.filepath, columns=required)
        
    # Run model
    results = ModelingService.run_model(df, model_type, target, features)
    
    return jsonify({
        'message': 'Model run successfully',
        'results': results
    }), 200

@modeling_bp.route('/export', methods=['POST'])
@token_required
def export_model(current_user):
    data = request.get_json()
    project_id = data.get('project_id')
    dataset_id = data.get('dataset_id')
    model_type = data.get('model_type')
    target = data.get('target')
    features = data.get('features')
    
    if not all([project_id, dataset_id, model_type, target, features]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # Load data
    required = [target] + features
    # Dedup
    required = list(set(required))
    
    df = DataService.load_data_optimized(dataset.filepath, columns=required)
        
    # Run model
    results = ModelingService.run_model(df, model_type, target, features)
    
    # Export
    from app.services.export_service import ExportService
    filename = f"results_{project_id}_{model_type}.xlsx"
    filepath = ExportService.export_results_to_excel(results, filename)
    
    return jsonify({
        'message': 'Export successful',
        'download_url': f"/api/data/download/{filename}" # Need a download endpoint
    }), 200

@modeling_bp.route('/select-variables', methods=['POST'])
@token_required
def select_variables(current_user):
    """
    执行自动化变量筛选。
    """
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    model_type = data.get('model_type', 'linear')
    target = data.get('target')
    features = data.get('features', [])
    method = data.get('method', 'stepwise') # stepwise, lasso
    params = data.get('params', {})
    
    if not all([dataset_id, model_type, target, features]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    # 过滤特征名
    feature_names = []
    for f in features:
        if isinstance(f, dict):
            feature_names.append(f.get('name') or f.get('value'))
        else:
            feature_names.append(str(f))
    
    # 加载必要数据
    required_cols = list(feature_names)
    if isinstance(target, dict):
        required_cols.extend(target.values())
    else:
        required_cols.append(target)
    
    required = list(set(required_cols))
    df = DataService.load_data_optimized(dataset.filepath, columns=required)
    
    # 执行筛选
    from app.services.model_selection_service import ModelSelectionService
    
    try:
        if method == 'stepwise':
            direction = params.get('direction', 'both')
            criterion = params.get('criterion', 'aic')
            results = ModelSelectionService.run_stepwise_selection(
                df, target, feature_names, model_type, direction, criterion
            )
        elif method == 'lasso':
            results = ModelSelectionService.run_lasso_selection(
                df, target, feature_names, model_type
            )
        else:
            return jsonify({'message': f'Unknown selection method: {method}'}), 400
            
        return jsonify(results), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'message': str(e)}), 500
