from flask import Blueprint, jsonify, request
from app.services.preprocessing_service import PreprocessingService
from app.models.dataset import Dataset
from app.api.projects import token_required

preprocessing_bp = Blueprint('preprocessing', __name__)

@preprocessing_bp.route('/impute', methods=['POST'])
@token_required
def impute(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    strategies = data.get('strategies') # {col: method}
    
    if not dataset_id or not strategies:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    # Check permissions (omitted for MVP speed)
    
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        new_df = PreprocessingService.impute_data(df, strategies)
        new_dataset = PreprocessingService.save_processed_dataset(dataset_id, new_df, 'imputed', current_user.id)
        return jsonify({'message': 'Imputation successful', 'new_dataset_id': new_dataset.dataset_id}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@preprocessing_bp.route('/encode', methods=['POST'])
@token_required
def encode(current_user):
    data = request.get_json()
    dataset_id = data.get('dataset_id')
    columns = data.get('columns') # [col1, col2]
    
    if not dataset_id or not columns:
        return jsonify({'message': 'Missing arguments'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        new_df = PreprocessingService.encode_data(df, columns)
        new_dataset = PreprocessingService.save_processed_dataset(dataset_id, new_df, 'encoded', current_user.id)
        return jsonify({'message': 'Encoding successful', 'new_dataset_id': new_dataset.dataset_id}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
