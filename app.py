# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from config import Config
from models import db, User, Video, WatchHistory, HomePageContent,Message
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

# Create tables and populate with initial videos and home content if the database is empty
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
        upcoming_video = Video(
            title=upcoming_title,
            youtube_id="UPCOMING_VIDEO_PLACEHOLDER", # Unique placeholder ID
            is_upcoming=True,
            release_date=datetime.datetime(2025, 7, 1)
        )
        db.session.add(upcoming_video)
        db.session.commit()

    # --- Initialize default Home Page Content ---
    home_message_name = "welcome_message"
    existing_home_message = HomePageContent.query.filter_by(section_name=home_message_name).first()
    if not existing_home_message:
        default_content = "Welcome to NIENTH CUT STUDIOS. Explore our latest videos and upcoming releases!"
        new_home_content = HomePageContent(section_name=home_message_name, content=default_content)
        db.session.add(new_home_content)
        db.session.commit()
        print(f"Default home page content for '{home_message_name}' created.")
    else:
        print(f"Home page content for '{home_message_name}' already exists.")


    # --- IMPORTANT: Set '9thcutstudios' user as developer ---
    # This assumes '9thcutstudios' user already exists in your database.
    # If not, you need to sign up as '9thcutstudios' first.
    target_developer_username = "9thcutstudios"
    user_to_set_as_dev = User.query.filter_by(username=target_developer_username).first()

    if user_to_set_as_dev:
        if not user_to_set_as_dev.is_developer:
            user_to_set_as_dev.is_developer = True
            db.session.commit()
            print(f"User '{target_developer_username}' successfully set as developer.")
        else:
            print(f"User '{target_developer_username}' is already a developer.")
    else:
        print(f"User '{target_developer_username}' not found. Please ensure this user exists in the database to enable developer features.")

@app.route('/community', methods=['GET', 'POST'])
def community():
    if 'user_id' not in session:
        flash('Please log in to access the community.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            new_msg = Message(content=content, user_id=session['user_id'])
            db.session.add(new_msg)
            db.session.commit()
            flash('Message posted!', 'success')

    messages = Message.query.order_by(Message.timestamp.desc()).all()
    user = User.query.get(session['user_id'])
    return render_template('community.html', messages=messages, username=user.username)

@app.route('/')
def index():
    user = None
    is_developer = False # Default to False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.is_developer:
            is_developer = True # Set to True if logged-in user is developer

    # Fetch only the latest 1 regular video for the home section
    latest_home_video = Video.query.filter_by(is_upcoming=False).order_by(Video.id.desc()).first()
    
    # Fetch all regular videos for the general 'Videos' section
    all_regular_videos = Video.query.filter_by(is_upcoming=False).all()

    upcoming_videos = Video.query.filter_by(is_upcoming=True).order_by(Video.release_date).all()

    # Fetch home page content
    home_content_obj = HomePageContent.query.filter_by(section_name="welcome_message").first()
    home_message = home_content_obj.content if home_content_obj else "Welcome to NIENTH CUT STUDIOS!"


    return render_template('index.html',
                           user=user,
                           latest_home_video=latest_home_video, # Pass the single latest video
                           regular_videos=all_regular_videos, # All regular videos for the VIDEOS tab
                           upcoming_videos=upcoming_videos,
                           is_developer=is_developer,
                           home_message=home_message) # Pass home_message to template

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

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
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session.permanent = True # Make the session persistent
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    # To clear persistent session:
    session.clear()
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
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{session['user_id']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        user = User.query.get(session['user_id'])
        if user:
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

    video = Video.query.get(video_id)
    if not video:
        return jsonify({'success': False, 'message': 'Video not found'}), 404

    existing_entry = WatchHistory.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing_entry:
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
        # For general search, return all regular videos
        videos = Video.query.filter_by(is_upcoming=False).all()
    else:
        videos = Video.query.filter(Video.title.ilike(f'%{query}%'), Video.is_upcoming==False).all()

    results = []
    for video in videos:
        results.append({
            'id': video.id,
            'title': video.title,
            'youtube_id': video.youtube_id
        })
    return jsonify({'success': True, 'videos': results})

# --- Developer Dashboard and Upload/Edit Functionality ---
@app.route('/developer_dashboard', methods=['GET'])
def developer_dashboard():
    if 'user_id' not in session:
        flash('Unauthorized access. Please log in.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_developer:
        flash('Access denied. You must be a developer to access this page.', 'error')
        return redirect(url_for('index'))

    # Fetch all videos to display in the list for editing/uploading
    current_videos = Video.query.all()

    # Fetch home page content for editing in dashboard
    home_content_obj = HomePageContent.query.filter_by(section_name="welcome_message").first()
    home_page_text = home_content_obj.content if home_content_obj else ""

    return render_template('developer_dashboard.html',
                           user=user,
                           current_videos=current_videos,
                           video_to_edit=None, # This is for the video form
                           home_page_text=home_page_text) # Pass home page text to dashboard

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'user_id' not in session:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_developer:
        flash('Access denied. Only developers can upload videos.', 'error')
        return redirect(url_for('index'))

    title = request.form.get('title')
    youtube_id = request.form.get('youtube_id')
    is_upcoming = request.form.get('is_upcoming') == 'on'
    release_date_str = request.form.get('release_date')

    if not title or not youtube_id:
        flash('Title and YouTube ID are required.', 'error')
        return redirect(url_for('developer_dashboard'))

    release_date = None
    if is_upcoming and release_date_str:
        try:
            release_date = datetime.datetime.strptime(release_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format for upcoming video.', 'error')
            return redirect(url_for('developer_dashboard'))
    elif is_upcoming and not release_date_str:
        flash('Release date is required for upcoming videos.', 'error')
        return redirect(url_for('developer_dashboard'))

    # Check for existing YouTube ID to prevent duplicates on NEW upload
    existing_video = Video.query.filter_by(youtube_id=youtube_id).first()
    if existing_video:
        flash(f'A video with YouTube ID "{youtube_id}" already exists. Use the edit feature if you want to modify it.', 'error')
        return redirect(url_for('developer_dashboard'))

    new_video = Video(
        title=title,
        youtube_id=youtube_id,
        is_upcoming=is_upcoming,
        release_date=release_date
    )

    db.session.add(new_video)
    db.session.commit()
    flash('Video uploaded successfully!', 'success')
    return redirect(url_for('developer_dashboard'))

@app.route('/edit_video/<int:video_id>', methods=['GET', 'POST'])
def edit_video(video_id):
    if 'user_id' not in session:
        flash('Unauthorized access. Please log in.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_developer:
        flash('Access denied. Only developers can edit videos.', 'error')
        return redirect(url_for('index'))

    video = Video.query.get_or_404(video_id)

    if request.method == 'POST':
        # Process the update
        video.title = request.form.get('title')
        new_youtube_id = request.form.get('youtube_id')
        video.is_upcoming = request.form.get('is_upcoming') == 'on'
        release_date_str = request.form.get('release_date')

        if not video.title or not new_youtube_id:
            flash('Title and YouTube ID are required.', 'error')
            return redirect(url_for('edit_video', video_id=video.id))

        # Check if the new YouTube ID is different and if it already exists for another video
        if new_youtube_id != video.youtube_id:
            existing_video_with_new_id = Video.query.filter_by(youtube_id=new_youtube_id).first()
            if existing_video_with_new_id and existing_video_with_new_id.id != video.id:
                flash(f'The YouTube ID "{new_youtube_id}" is already used by another video. Please use a unique ID.', 'error')
                return redirect(url_for('edit_video', video_id=video.id))
        video.youtube_id = new_youtube_id

        if video.is_upcoming and release_date_str:
            try:
                video.release_date = datetime.datetime.strptime(release_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for upcoming video.', 'error')
                return redirect(url_for('edit_video', video_id=video.id))
        elif video.is_upcoming and not release_date_str:
            flash('Release date is required for upcoming videos.', 'error')
            return redirect(url_for('edit_video', video_id=video.id))
        else: # Not upcoming, so clear release date
            video.release_date = None

        db.session.commit()
        flash('Video updated successfully!', 'success')
        return redirect(url_for('developer_dashboard'))
    else:
        # Display the edit form for the specific video
        current_videos = Video.query.all() # Still pass all videos for the list on the side
        home_content_obj = HomePageContent.query.filter_by(section_name="welcome_message").first()
        home_page_text = home_content_obj.content if home_content_obj else ""

        return render_template('developer_dashboard.html',
                               user=user,
                               current_videos=current_videos,
                               video_to_edit=video, # Pass the specific video to pre-fill the form
                               home_page_text=home_page_text)

@app.route('/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if 'user_id' not in session:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_developer:
        flash('Access denied. Only developers can delete videos.', 'error')
        return redirect(url_for('index'))

    video = Video.query.get_or_404(video_id)
    title = video.title # Store title for flash message

    # Delete associated watch history entries first to avoid foreign key constraints
    WatchHistory.query.filter_by(video_id=video.id).delete()
    db.session.delete(video)
    db.session.commit()
    flash(f'Video "{title}" deleted successfully!', 'success')
    return redirect(url_for('developer_dashboard'))

# NEW: Route to manage home page content
@app.route('/manage_home_content', methods=['POST'])
def manage_home_content():
    if 'user_id' not in session:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_developer:
        flash('Access denied. Only developers can manage home page content.', 'error')
        return redirect(url_for('index'))

    new_content = request.form.get('home_welcome_message')

    if not new_content:
        flash('Home page message cannot be empty.', 'error')
        return redirect(url_for('developer_dashboard'))

    home_content_obj = HomePageContent.query.filter_by(section_name="welcome_message").first()

    if home_content_obj:
        home_content_obj.content = new_content
        db.session.commit()
        flash('Home page message updated successfully!', 'success')
    else:
        # This case should ideally not happen if initial creation is correct, but added for robustness
        new_home_content = HomePageContent(section_name="welcome_message", content=new_content)
        db.session.add(new_home_content)
        db.session.commit()
        flash('Home page message created successfully!', 'success')

    return redirect(url_for('developer_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
