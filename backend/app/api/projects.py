from flask import Blueprint, request, jsonify
from app import db
from app.models.project import Project
from flask import Blueprint, request, jsonify
from app import db
from app.models.project import Project
from app.api.middleware import token_required

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/', methods=['GET'])
@token_required
def get_projects(current_user):
    projects = current_user.projects.all()
    output = []
    for project in projects:
        project_data = {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'created_at': project.created_at
        }
        output.append(project_data)
    return jsonify({'projects': output}), 200

@projects_bp.route('/', methods=['POST'])
@token_required
def create_project(current_user):
    data = request.get_json()
    new_project = Project(name=data['name'], description=data.get('description', ''), author=current_user)
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'message': 'Project created', 'id': new_project.id}), 201

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@token_required
def delete_project(current_user, project_id):
    project = Project.query.get_or_404(project_id)
    if project.author != current_user:
        return jsonify({'message': 'Permission denied'}), 403
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted'}), 200
