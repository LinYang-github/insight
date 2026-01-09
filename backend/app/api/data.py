from flask import Blueprint, request, jsonify, current_app, send_from_directory
from app.api.projects import token_required
from app.services.data_service import DataService
from app.models.project import Project
from app import db
import os

data_bp = Blueprint('data', __name__)

from app.models.dataset import Dataset

@data_bp.route('/upload/<int:project_id>', methods=['POST'])
@token_required
def upload_data(current_user, project_id):
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
    
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file:
        try:
            # Save file
            filename = f"project_{project_id}_{file.filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            # Parse and get metadata
            metadata = DataService.get_initial_metadata(filepath)
            
            # Save to Database
            new_dataset = Dataset(
                project_id=project.id,
                name=file.filename,
                filepath=filepath
            )
            new_dataset.meta_data = metadata
            db.session.add(new_dataset)
            db.session.commit()
            
            return jsonify({
                'message': 'File uploaded successfully', 
                'dataset_id': new_dataset.id,
                'metadata': metadata
            }), 201
        except Exception as e:
            return jsonify({'message': str(e)}), 500

@data_bp.route('/metadata/<int:project_id>', methods=['GET'])
@token_required
def get_metadata(current_user, project_id):
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
    
    # for MVP, assume one dataset per project or get the latest
    dataset = Dataset.query.filter_by(project_id=project.id).order_by(Dataset.created_at.desc()).first()
    
    if not dataset:
         return jsonify({'message': 'No dataset found for this project'}), 404
         
    return jsonify({
        'dataset_id': dataset.id,
        'name': dataset.name,
        'metadata': dataset.meta_data,
        'created_at': dataset.created_at
    }), 200
         
@data_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    # Security: Ensure filename is safe (simple check for now)
    if '..' in filename or '/' in filename:
         return jsonify({'message': 'Invalid filename'}), 400
         
    directory = current_app.config['UPLOAD_FOLDER']
    path = os.path.join(directory, filename)
    
    if not os.path.exists(path):
        return jsonify({'message': 'File not found'}), 404
        
    return send_from_directory(directory, filename, as_attachment=True)
