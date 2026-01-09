from flask import Blueprint, request, jsonify
from app.api.middleware import token_required
from app import db
from app.models import User

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/get', methods=['GET'])
@token_required
def get_settings(current_user):
    """
    获取当前用户的个性化设置。
    """
    # Default settings structure
    defaults = {
        "theme": "light",
        "p_value": 0.05,
        "digits": 3
    }
    
    # Merge user settings with defaults
    user_settings = current_user.settings or {}
    final_settings = {**defaults, **user_settings}
    
    return jsonify(final_settings), 200

@settings_bp.route('/update', methods=['PUT'])
@token_required
def update_settings(current_user):
    """
    更新用户个性化设置。
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400
        
    current_settings = current_user.settings or {}
    
    # Update only allowed keys to prevent pollution
    allowed_keys = ['theme', 'p_value', 'digits']
    for key in allowed_keys:
        if key in data:
            current_settings[key] = data[key]
            
    # SQLAlchemy requires flagging JSON fields as modified sometimes, 
    # but reassigning a new dict works best
    current_user.settings = dict(current_settings) 
    
    try:
        db.session.commit()
        return jsonify({'message': 'Settings updated', 'settings': current_user.settings}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500
