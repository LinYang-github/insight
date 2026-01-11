from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    db.create_all() # Ensure tables exist
    if not User.query.filter_by(username='admin').first():
        user = User(username='admin', email='admin@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        print("User 'admin' created with password 'password'")
    else:
        print("User 'admin' already exists")
