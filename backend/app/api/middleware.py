from functools import wraps
from flask import request, jsonify
import jwt
from app import db
from app.models.user import User
from app.config import Config

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.split(" ")[1] # Bearer <token>
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user = db.session.get(User, data['user_id'])
            if current_user is None:
                return jsonify({'message': 'User not found'}), 401
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated
