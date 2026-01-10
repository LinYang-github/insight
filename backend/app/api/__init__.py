
from flask import Blueprint
from .auth import auth_bp
from .projects import projects_bp
from .data import data_bp
from .modeling import modeling_bp
from .eda import eda_bp
from .preprocessing import preprocessing_bp
from .statistics import statistics_bp
from .settings import settings_bp
from .clinical import clinical_bp

main_bp = Blueprint('api', __name__)

def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(modeling_bp, url_prefix='/api/modeling')
    app.register_blueprint(eda_bp, url_prefix='/api/eda')
    app.register_blueprint(preprocessing_bp, url_prefix='/api/preprocessing')
    app.register_blueprint(statistics_bp, url_prefix='/api/statistics')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(clinical_bp, url_prefix='/api/clinical')
    
    from .advanced import advanced_bp
    app.register_blueprint(advanced_bp, url_prefix='/api/advanced')

    from .validation import validation_bp
    app.register_blueprint(validation_bp, url_prefix='/api/validation')

    from .longitudinal import longitudinal_bp
    app.register_blueprint(longitudinal_bp, url_prefix='/api/longitudinal')
