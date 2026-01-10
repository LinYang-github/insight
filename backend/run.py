from app import create_app, db
from app.models import User, Project

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Project': Project}

if __name__ == '__main__':
    print(f"DEBUG: Internal Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(debug=True, port=5000)
