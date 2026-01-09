from flask import Blueprint, jsonify, request
from app.services.eda_service import EdaService
from app.models.dataset import Dataset
from app.models.project import Project
from app.api.projects import token_required

eda_bp = Blueprint('eda', __name__)

@eda_bp.route('/stats/<int:dataset_id>', methods=['GET'])
@token_required
def get_stats(current_user, dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    # Permission check or project check
    
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        stats = EdaService.get_basic_stats(df)
        return jsonify({'stats': stats}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@eda_bp.route('/correlation/<int:dataset_id>', methods=['GET'])
@token_required
def get_correlation(current_user, dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        corr_data = EdaService.get_correlation(df)
        return jsonify(corr_data), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@eda_bp.route('/distribution/<int:dataset_id>/<string:column>', methods=['GET'])
@token_required
def get_distribution(current_user, dataset_id, column):
    dataset = Dataset.query.get_or_404(dataset_id)
    try:
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
        dist_data = EdaService.get_distribution(df, column)
        return jsonify(dist_data), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
