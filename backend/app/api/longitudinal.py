from flask import Blueprint, request, jsonify
from app.api.projects import token_required
from app.services.longitudinal_service import LongitudinalService
from app.models.project import Project
from app.models.dataset import Dataset
from app.services.data_service import DataService

longitudinal_bp = Blueprint('longitudinal', __name__)

@longitudinal_bp.route('/lmm', methods=['POST'])
@token_required
def fit_lmm(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    fixed_effects = data.get('fixed_effects', [])
    
    # ID, Time, Outcome are mapped by user
    id_col = data.get('id_col')
    time_col = data.get('time_col')
    outcome_col = data.get('outcome_col')
    
    if not all([dataset_id, id_col, time_col, outcome_col]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    df = DataService.load_data(dataset.filepath)
    
    try:
        results = LongitudinalService.fit_lmm(df, id_col, time_col, outcome_col, fixed_effects)
        return jsonify({'status': 'success', 'results': results}), 200
    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 400

@longitudinal_bp.route('/clustering', methods=['POST'])
@token_required
def cluster_trajectories(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    id_col = data.get('id_col')
    time_col = data.get('time_col')
    outcome_col = data.get('outcome_col')
    n_clusters = data.get('n_clusters', 3)
    
    if not all([dataset_id, id_col, time_col, outcome_col]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    df = DataService.load_data(dataset.filepath)
    
    try:
        results = LongitudinalService.cluster_trajectories(df, id_col, time_col, outcome_col, n_clusters)
        return jsonify({'status': 'success', 'results': results}), 200
    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 400

@longitudinal_bp.route('/variability', methods=['POST'])
@token_required
def calculate_variability(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    id_col = data.get('id_col')
    outcome_col = data.get('outcome_col')
    
    if not all([dataset_id, id_col, outcome_col]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    df = DataService.load_data(dataset.filepath)
    
    try:
        results = LongitudinalService.calculate_variability(df, id_col, outcome_col)
        return jsonify({'status': 'success', 'results': results}), 200
    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 400

@longitudinal_bp.route('/ai-suggest-roles', methods=['POST'])
@token_required
def ai_suggest_roles(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    
    if not dataset_id:
        return jsonify({'message': 'Missing dataset_id'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    if not dataset or not dataset.meta_data:
        return jsonify({'message': 'Dataset metadata not found'}), 404
        
    user_settings = current_user.settings or {}
    api_key = user_settings.get('llm_key')
    api_base = user_settings.get('llm_api_base') or "https://api.openai.com/v1"
    api_model = user_settings.get('llm_model') or "gpt-4o"
    
    if not api_key:
        return jsonify({'message': '未配置 AI API Key'}), 400
        
    from app.services.ai_service import AIService
    try:
        recommendations = AIService.suggest_advanced_roles(
            'longitudinal', dataset.meta_data['variables'],
            api_key, api_base, api_model
        )
        return jsonify(recommendations), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@longitudinal_bp.route('/ai-interpret-longitudinal', methods=['POST'])
@token_required
def ai_interpret_longitudinal(current_user):
    data = request.get_json()
    analysis_type = data.get('analysis_type') # lmm, clustering
    results = data.get('results')
    
    # Context vars
    target = data.get('target') # outcome_col
    time_col = data.get('time_col')
    
    if not analysis_type or not results:
        return jsonify({'message': 'Missing required data'}), 400
        
    user_settings = current_user.settings or {}
    api_key = user_settings.get('llm_key')
    api_base = user_settings.get('llm_api_base') or "https://api.openai.com/v1"
    api_model = user_settings.get('llm_model') or "gpt-4o"
    
    if not api_key:
        return jsonify({'message': '未配置 AI API Key'}), 400
        
    from app.services.ai_service import AIService
    try:
        if analysis_type == 'lmm':
            interpretation = AIService.interpret_lmm(
                results, target, time_col,
                api_key, api_base, api_model
            )
        elif analysis_type == 'clustering':
            interpretation = AIService.interpret_clustering(
                results, time_col, target,
                api_key, api_base, api_model
            )
        else:
            return jsonify({'message': 'Unknown analysis type'}), 400
            
        return jsonify({'interpretation': interpretation}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
