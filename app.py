from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from config import Config
from models import db, User, Video, WatchHistory
import os
from werkzeug.utils import secure_filename
import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- DUMMY DATA WITH CORRECT YOUTUBE IDs ---
DUMMY_VIDEOS = [
    {"id": 1, "title": "PEAY LINEAR FORM", "youtube_id": "d8TZ_zImSE8"},
    {"id": 2, "title": "PEAY official movie", "youtube_id": "WrcLcQqvlV4"},
    {"id": 3, "title": "PEAY trailer", "youtube_id": "2Y98bsZq3BU"},
    {"id": 4, "title": "Fear wave the music video", "youtube_id": "1J9g5z-MzL8"},
]

# Create tables and populate with initial videos if the database is empty
with app.app_context():
    db.create_all()
    # Add some initial videos if the database is empty (or if specific videos don't exist)
    for video_data in DUMMY_VIDEOS:
        existing_video = Video.query.filter_by(youtube_id=video_data['youtube_id']).first()
        if not existing_video:
            new_video = Video(title=video_data['title'], youtube_id=video_data['youtube_id'])
            db.session.add(new_video)
    db.session.commit()

    # Add an upcoming video (ensure it's not added multiple times)
    upcoming_title = "Behind The Scenes - Editing Secrets"
    existing_upcoming = Video.query.filter_by(title=upcoming_title, is_upcoming=True).first()
    if not existing_upcoming:
        # IMPORTANT FIX: Assign a placeholder YouTube ID for upcoming videos
        upcoming_video = Video(
            title=upcoming_title,
            youtube_id="UPCOMING_VIDEO_PLACEHOLDER", # Unique placeholder ID
            is_upcoming=True,
            release_date=datetime.datetime(2025, 7, 1)
        )
        db.session.add(upcoming_video)
        db.session.commit()


@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])

    # Fetch videos for display (you might want to paginate or filter these)
    regular_videos = Video.query.filter_by(is_upcoming=False).all()
    upcoming_videos = Video.query.filter_by(is_upcoming=True).order_by(Video.release_date).all()

    return render_template('index.html', user=user, regular_videos=regular_videos, upcoming_videos=upcoming_videos)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index')) # Redirect logged-in users from signup

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index')) # Redirect logged-in users from login

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/change_profile_photo', methods=['POST'])
def change_profile_photo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    if 'profile_photo' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400

    file = request.files['profile_photo']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        # Ensure unique filename to prevent collisions and security issues
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{session['user_id']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        user = User.query.get(session['user_id'])
        if user:
            # Delete old profile photo if it's not the default
            if user.profile_photo and user.profile_photo != 'default.png':
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_photo)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            user.profile_photo = unique_filename
            db.session.commit()
            return jsonify({'success': True, 'message': 'Profile photo updated successfully', 'new_photo_url': url_for('static', filename=f'profile_pics/{unique_filename}')})
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
    return jsonify({'success': False, 'message': 'File upload failed'}), 500

@app.route('/save_watch_history', methods=['POST'])
def save_watch_history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({'success': False, 'message': 'Video ID is required'}), 400

    user_id = session['user_id']

    # Check if video exists
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'success': False, 'message': 'Video not found'}), 404

    # Check if this watch entry already exists for the user and video
    existing_entry = WatchHistory.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing_entry:
        # Update timestamp if video is watched again
        existing_entry.watched_on = datetime.datetime.utcnow()
    else:
        new_entry = WatchHistory(user_id=user_id, video_id=video_id)
        db.session.add(new_entry)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Watch history updated'})

@app.route('/get_watch_history')
def get_watch_history():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    user_id = session['user_id']
    watch_entries = WatchHistory.query.filter_by(user_id=user_id).order_by(WatchHistory.watched_on.desc()).all()

    history_data = []
    for entry in watch_entries:
        video = Video.query.get(entry.video_id)
        if video:
            history_data.append({
                'video_title': video.title,
                'video_youtube_id': video.youtube_id,
                'watched_on': entry.watched_on.strftime('%Y-%m-%d %H:%M:%S')
            })
    return jsonify({'success': True, 'history': history_data})

@app.route('/search_videos', methods=['GET'])
def search_videos():
    query = request.args.get('q', '').lower()

    if not query:
        # If no query, return all non-upcoming videos
        videos = Video.query.filter_by(is_upcoming=False).all()
    else:
        # Search by title (case-insensitive)
        videos = Video.query.filter(Video.title.ilike(f'%{query}%'), Video.is_upcoming==False).all()

    results = []
    for video in videos:
        results.append({
            'id': video.id,
            'title': video.title,
            'youtube_id': video.youtube_id
        })
    return jsonify({'success': True, 'videos': results})


if __name__ == '__main__':
    app.run(debug=True)
