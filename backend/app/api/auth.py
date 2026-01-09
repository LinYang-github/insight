from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
import jwt
import datetime
from app.config import Config
from app.api.middleware import token_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists'}), 400
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, Config.SECRET_KEY, algorithm='HS256')
        
        return jsonify({'token': token, 'username': user.username}), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401
@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'message': 'Missing arguments'}), 400
        
    if not current_user.check_password(current_password):
        return jsonify({'message': 'Invalid current password'}), 401
        
    current_user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Password updated successfully'}), 200
