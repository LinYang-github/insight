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
