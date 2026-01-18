import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from app.models import User

app = create_app()

with app.app_context():
    u = User.query.filter_by(username='admin').first()
    if u:
        print(f"User found: {u.username}, {u.email}")
        print(f"Password hash: {u.password_hash}")
        is_valid = u.check_password('admin123')
        print(f"Check 'admin123': {is_valid}")
    else:
        print("User 'admin' not found.")