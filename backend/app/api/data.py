"""
app.api.data.py

数据管理接口。
提供数据上传、元数据查询及结果文件下载功能。
"""
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
    """
    上传数据集文件。
    
    支持并发存入文件系统，并自动提取变量元数据存入数据库。
    """
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
    
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file:
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
        db.session.flush() # Get ID
        project.active_dataset_id = new_dataset.id
        db.session.commit()
        
        return jsonify({
            'message': 'File uploaded successfully', 
            'dataset_id': new_dataset.id,
            'metadata': metadata
        }), 201

@data_bp.route('/metadata/<int:project_id>', methods=['GET'])
@token_required
def get_metadata(current_user, project_id):
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
    
    # Prioritize active_dataset_id
    if project.active_dataset_id:
        dataset = Dataset.query.get(project.active_dataset_id)
        if dataset and dataset.project_id != project.id:
            dataset = None # Safety check
            
    if not project.active_dataset_id or not dataset:
        # Fallback to latest
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
    return send_from_directory(directory, filename, as_attachment=True)

@data_bp.route('/<int:dataset_id>', methods=['DELETE'])
@token_required
def delete_dataset(current_user, dataset_id):
    """
    物理删除数据集。
    """
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
        
    # File removal is handled by SQLAlchemy event listener in models/dataset.py:receive_after_delete
    db.session.delete(dataset)
    db.session.commit()
    return jsonify({'message': 'Dataset deleted successfully'}), 200

@data_bp.route('/<int:dataset_id>/rename', methods=['PUT'])
@token_required
def rename_dataset(current_user, dataset_id):
    """
    重命名数据集 (仅修改显示名称).
    """
    data = request.get_json()
    new_name = data.get('name')
    
    if not new_name:
        return jsonify({'message': 'New name is required'}), 400
        
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
        
    dataset.name = new_name
    db.session.commit()
    return jsonify({'message': 'Dataset renamed successfully'}), 200
