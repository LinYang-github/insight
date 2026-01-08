from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from .config import Config

db = SQLAlchemy()
migrate = Migrate()

import os

def create_app(config_class=Config):
    # Calculate absolute path to frontend/dist
    # current file: backend/app/__init__.py
    # we want: insight/frontend/dist
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

    return app
