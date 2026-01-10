from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from .config import Config

db = SQLAlchemy()
migrate = Migrate()

import os
import sys

def create_app(config_class=Config):
    # Calculate absolute path to frontend/dist
    if getattr(sys, 'frozen', False):
        # In a bundled executable, static files are usually added to the bundle root or a subdirectory
        # PyInstaller extracts to sys._MEIPASS
        static_folder = os.path.join(sys._MEIPASS, 'frontend/dist')
    else:
        # Development mode
        backend_app_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(backend_app_dir, '../..'))
        static_folder = os.path.join(project_root, 'frontend', 'dist')
    
    app = Flask(__name__, 
                static_folder=static_folder,
                static_url_path='/')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    from app.api import register_blueprints
    register_blueprints(app)

    @app.errorhandler(404)
    def not_found(e):
        from flask import request
        path = request.path
        if path.startswith('/api') or path.startswith('/assets'):
            # Return JSON for API 404s, or standard 404 for assets
            if path.startswith('/api'):
                return {'message': 'Not Found'}, 404
            return e
        # Serve index.html for SPA routes
        return app.send_static_file('index.html')

    @app.errorhandler(Exception)
    def handle_exception(e):
        from flask import jsonify
        # 记录完整堆栈信息
        app.logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)
        
        # 业务逻辑错误 (Business Logic Error) -> 400
        if isinstance(e, ValueError):
            return jsonify({
                "error": "BusinessError", 
                "message": str(e)
            }), 400
            
        # 其他未捕获异常 (Internal Server Error) -> 500
        return jsonify({
            "error": "InternalServerError", 
            "message": "系统繁忙，请联系管理员或查看日志。"
        }), 500

    return app
