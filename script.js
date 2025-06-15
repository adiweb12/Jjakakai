const API_BASE_URL = 'https://jjakakai.onrender.com';

// --- Helper Functions ---
function getAuthToken() {
    return localStorage.getItem('token');
}

function setAuthToken(token) {
    localStorage.setItem('token', token);
}

function removeAuthToken() {
    localStorage.removeItem('token');
}

function getLoggedInUsername() {
    return localStorage.getItem('username');
}

function setLoggedInUsername(username) {
    localStorage.setItem('username', username);
}

function removeLoggedInUsername() {
    localStorage.removeItem('username');
}

function showMessage(elementId, message, type = 'success') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.className = `message ${type}`;
        setTimeout(() => {
            element.textContent = '';
            element.className = 'message';
        }, 5000); // Clear message after 5 seconds
    }
}

function updateNav() {
    const token = getAuthToken();
    const username = getLoggedInUsername();
    const signupLink = document.querySelector('nav a[href="signup.html"]');
    const loginLink = document.querySelector('nav a[href="login.html"]');
    const logoutButton = document.getElementById('logoutButton');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const addVideoSection = document.getElementById('addVideoSection');

    if (token && username) {
        if (signupLink) signupLink.style.display = 'none';
        if (loginLink) loginLink.style.display = 'none';
        if (logoutButton) logoutButton.style.display = 'inline';
        if (welcomeMessage) welcomeMessage.textContent = `Welcome, ${username}!`;
        if (addVideoSection) addVideoSection.style.display = 'block'; // Show add video for logged in users
    } else {
        if (signupLink) signupLink.style.display = 'inline';
        if (loginLink) loginLink.style.display = 'inline';
        if (logoutButton) logoutButton.style.display = 'none';
        if (welcomeMessage) welcomeMessage.textContent = '';
        if (addVideoSection) addVideoSection.style.display = 'none'; // Hide add video for guests
    }
}

function getYouTubeEmbedUrl(youtubeUrl) {
    let videoId = '';
    const regExp = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = youtubeUrl.match(regExp);
    if (match) {
        videoId = match[1];
        return `https://www.youtube.com/embed/${videoId}?autoplay=0&modestbranding=1&rel=0`;
    }
    return null;
}

// --- Event Handlers ---

// Handle Sign Up Form
document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('signupUsername').value;
            const password = document.getElementById('signupPassword').value;

            try {
                const response = await fetch(`${API_BASE_URL}/signup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await response.json();

                if (response.ok) {
                    showMessage('signupMessage', data.message, 'success');
                    signupForm.reset();
                    // Optionally redirect to login page after successful signup
                    setTimeout(() => window.location.href = 'login.html', 2000);
                } else {
                    showMessage('signupMessage', data.message, 'error');
                }
            } catch (error) {
                console.error('Signup error:', error);
                showMessage('signupMessage', 'An error occurred during signup.', 'error');
            }
        });
    }

    // Handle Login Form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;

            try {
                const response = await fetch(`${API_BASE_URL}/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await response.json();

                if (response.ok) {
                    setAuthToken(data.token);
                    setLoggedInUsername(data.username);
                    showMessage('loginMessage', data.message, 'success');
                    loginForm.reset();
                    // Redirect to home page after successful login
                    setTimeout(() => window.location.href = 'index.html', 1000);
                } else {
                    showMessage('loginMessage', data.message, 'error');
                }
            } catch (error) {
                console.error('Login error:', error);
                showMessage('loginMessage', 'An error occurred during login.', 'error');
            }
        });
    }

    // Handle Logout Button
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            removeAuthToken();
            removeLoggedInUsername();
            updateNav();
            // Refresh videos or redirect to ensure content is guest-view only
            if (window.location.pathname.endsWith('index.html') || window.location.pathname === '/') {
                loadVideos(); // Reload videos to reflect guest state
            } else {
                window.location.href = 'index.html'; // Go to home if on another page
            }
        });
    }

    // Handle Add Video Form
    const addVideoForm = document.getElementById('addVideoForm');
    if (addVideoForm) {
        addVideoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const title = document.getElementById('videoTitle').value;
            const youtubeUrl = document.getElementById('youtubeUrl').value;
            const token = getAuthToken();

            if (!token) {
                showMessage('addVideoMessage', 'Please login to add videos.', 'error');
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/videos`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ title, youtubeUrl })
                });
                const data = await response.json();

                if (response.ok) {
                    showMessage('addVideoMessage', data.message, 'success');
                    addVideoForm.reset();
                    loadVideos(); // Reload videos to show the newly added one
                } else {
                    showMessage('addVideoMessage', data.message, 'error');
                }
            } catch (error) {
                console.error('Add video error:', error);
                showMessage('addVideoMessage', 'An error occurred while adding video.', 'error');
            }
        });
    }

    // Initial load and update for index.html
    if (document.getElementById('videoList')) {
        updateNav();
        loadVideos();
    }
});


// --- Video Loading and Liking ---

async function loadVideos() {
    const videoList = document.getElementById('videoList');
    if (!videoList) return; // Only run on index.html

    videoList.innerHTML = 'Loading videos...'; // Clear previous videos

    try {
        const response = await fetch(`${API_BASE_URL}/videos`);
        const videos = await response.json();

        videoList.innerHTML = ''; // Clear loading message

        if (videos.length === 0) {
            videoList.innerHTML = '<p>No videos available yet. Be the first to add one!</p>';
            return;
        }

        videos.forEach(video => {
            const embedUrl = getYouTubeEmbedUrl(video.youtubeUrl);
            if (!embedUrl) {
                console.warn(`Could not get embed URL for video: ${video.title} (${video.youtubeUrl})`);
                return; // Skip invalid YouTube URLs
            }

            const videoCard = document.createElement('div');
            videoCard.className = 'video-card';
            videoCard.innerHTML = `
                <div class="video-embed">
                    <iframe src="${embedUrl}" allowfullscreen></iframe>
                </div>
                <h3>${video.title}</h3>
                <div class="actions">
                    <button class="like-button" data-id="${video.id}">Like</button>
                    <span>${video.likes} Likes</span>
                </div>
            `;
            videoList.appendChild(videoCard);
        });

        // Add event listeners for like buttons after they are created
        document.querySelectorAll('.like-button').forEach(button => {
            button.addEventListener('click', handleLike);
        });

    } catch (error) {
        console.error('Error loading videos:', error);
        videoList.innerHTML = '<p>Error loading videos. Please try again later.</p>';
    }
}

async function handleLike(event) {
    const videoId = event.target.dataset.id;
    const token = getAuthToken();

    if (!token) {
        alert('You must be logged in to like videos.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/videos/${videoId}/like`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await response.json();

        if (response.ok) {
            alert(data.message); // Show success message
            // Update the like count on the UI without reloading all videos
            const likeCountSpan = event.target.nextElementSibling; // Get the span element
            if (likeCountSpan) {
                likeCountSpan.textContent = `${data.newLikes} Likes`;
            }
        } else {
            alert(`Error: ${data.message || 'Could not like video.'}`);
        }
    } catch (error) {
        console.error('Error liking video:', error);
        alert('An error occurred while liking the video.');
    }
}
