from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_photo = db.Column(db.String(255), default='default.png')
    is_developer = db.Column(db.Boolean, default=False)
    watch_history = db.relationship('WatchHistory', backref='user', lazy=True)
    messages = db.relationship('Message', backref='user', lazy=True)  # New relationship

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    youtube_id = db.Column(db.String(100), unique=True, nullable=False)
    is_upcoming = db.Column(db.Boolean, default=False)
    release_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Video {self.title}>'

class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    watched_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<WatchHistory User:{self.user_id} Video:{self.video_id}>'

# ✅ NEW: Community Messages Model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Message {self.user_id}: {self.content[:30]}>'

class HomePageContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_name = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'home_welcome_message'
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<HomePageContent {self.section_name}>'