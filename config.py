# config.py
import os
import datetime # Import datetime here

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_hard_to_guess_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'profile_pics')

    # Add for persistent sessions
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=7) # Session lasts for 7 days
