from flask import Blueprint, request, jsonify
from app.api.projects import token_required
from app.services.modeling_service import ModelingService
from app.models.project import Project
from app.models.dataset import Dataset
import pandas as pd
import os # missing import fixed

modeling_bp = Blueprint('modeling', __name__)

@modeling_bp.route('/run', methods=['POST'])
@token_required
def run_model(current_user):
    data = request.get_json()
    
    project_id = data.get('project_id')
    dataset_id = data.get('dataset_id')
    model_type = data.get('model_type') # linear, logistic, cox
    target = data.get('target')
    features = data.get('features')
    
    # Validation
    if not all([project_id, dataset_id, model_type, target, features]):
        return jsonify({'message': 'Missing required parameters'}), 400
        
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
        
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.project_id != project.id:
        return jsonify({'message': 'Dataset does not belong to project'}), 400
        
    try:
        # Load data
        # Load data
        # Use robust loading from DataService
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
            
        # Run model
        results = ModelingService.run_model(df, model_type, target, features)
        
        return jsonify({
            'message': 'Model run successfully',
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

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
    
    try:
        # Load data
        # Load data
        from app.services.data_service import DataService
        df = DataService.load_data(dataset.filepath)
            
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
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500
