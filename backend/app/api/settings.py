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
        "digits": 3,
        "llm_key": "",
        "llm_api_base": "https://api.openai.com/v1",
        "llm_model": "gpt-4o"
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
        
    # Create a deep copy to ensure we aren't modifying a shared reference in-place
    # which can lead to SQLAlchemy not detecting the change.
    import copy
    current_settings = copy.deepcopy(current_user.settings or {})
    
    # Update only allowed keys to prevent pollution
    allowed_keys = ['theme', 'p_value', 'digits', 'llm_key', 'llm_api_base', 'llm_model']
    for key in allowed_keys:
        if key in data:
            current_settings[key] = data[key]
            
    # Assigning a new object reference
    current_user.settings = current_settings
    
    # Explicitly flag the JSON field as modified for SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(current_user, 'settings')
    
    print(f"DEBUG: Saving settings for user {current_user.username}: {current_settings}")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Save failed: {e}")
        return jsonify({'message': f'Database error: {str(e)}'}), 500
        
    return jsonify({'message': 'Settings updated', 'settings': current_user.settings}), 200
