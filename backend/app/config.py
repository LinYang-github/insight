import os
import sys

class Config:
    # Detect if we are running in a bundled executable (PyInstaller)
    IS_FROZEN = getattr(sys, 'frozen', False)
    
    # BASE_DIR for persistence (database, uploads) should be CWD
    # This allows the user to run the .exe anywhere and keep data locally
    BASE_DIR = os.getcwd()
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # SQLite DB in CWD
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(BASE_DIR, 'insight.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads in CWD
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data')

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
