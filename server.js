const express = require('express');
const fs = require('fs').promises; // For async file operations
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const cors = require('cors'); // Import cors

const app = express();
const PORT = 3000;
const SECRET_KEY = 'your_super_secret_key'; // CHANGE THIS IN PRODUCTION!

// Middleware
app.use(cors()); // Enable CORS for all routes
app.use(express.json()); // To parse JSON request bodies

// Database file path
const DB_FILE = 'db.json';

// Helper function to read/write DB
async function readDb() {
    try {
        const data = await fs.readFile(DB_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        // If file doesn't exist or is empty, return initial structure
        if (error.code === 'ENOENT' || error.name === 'SyntaxError') {
            return { users: [], videos: [] };
        }
        throw error; // Re-throw other errors
    }
}

async function writeDb(data) {
    await fs.writeFile(DB_FILE, JSON.stringify(data, null, 2), 'utf8');
}

// Initial DB structure if it's empty
async function initializeDb() {
    const db = await readDb();
    if (!db.users) db.users = [];
    if (!db.videos) db.videos = [];
    await writeDb(db);
}
initializeDb(); // Call once at server start

// Middleware to verify JWT token
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.sendStatus(401); // Unauthorized
    }

    jwt.verify(token, SECRET_KEY, (err, user) => {
        if (err) {
            console.error("JWT verification error:", err);
            return res.sendStatus(403); // Forbidden
        }
        req.user = user; // Attach user info to request
        next();
    });
};

// --- Routes ---

// 1. User Sign Up
app.post('/api/signup', async (req, res) => {
    const { username, password } = req.body;
    const db = await readDb();

    if (!username || !password) {
        return res.status(400).json({ message: 'Username and password are required.' });
    }

    if (db.users.find(u => u.username === username)) {
        return res.status(409).json({ message: 'Username already exists.' });
    }

    const hashedPassword = await bcrypt.hash(password, 10); // Hash password
    const newUser = { id: db.users.length + 1, username, password: hashedPassword };
    db.users.push(newUser);
    await writeDb(db);

    res.status(201).json({ message: 'User registered successfully!' });
});

// 2. User Login
app.post('/api/login', async (req, res) => {
    const { username, password } = req.body;
    const db = await readDb();

    const user = db.users.find(u => u.username === username);
    if (!user) {
        return res.status(400).json({ message: 'Invalid username or password.' });
    }

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
        return res.status(400).json({ message: 'Invalid username or password.' });
    }

    // Generate JWT token
    const token = jwt.sign({ id: user.id, username: user.username }, SECRET_KEY, { expiresIn: '1h' });
    res.json({ message: 'Logged in successfully!', token, username: user.username });
});

// 3. Get All Videos (Public)
app.get('/api/videos', async (req, res) => {
    const db = await readDb();
    // Return videos, stripping sensitive info like likedBy array if desired, or just return as is for simplicity
    res.json(db.videos.map(video => ({
        id: video.id,
        title: video.title,
        youtubeUrl: video.youtubeUrl,
        likes: video.likes // Send the current like count
    })));
});

// 4. Add a Video (Requires Authentication - for simplicity, anyone logged in can add)
app.post('/api/videos', authenticateToken, async (req, res) => {
    const { title, youtubeUrl } = req.body;
    if (!title || !youtubeUrl) {
        return res.status(400).json({ message: 'Title and YouTube URL are required.' });
    }

    // Basic YouTube URL validation (you can make this more robust)
    if (!youtubeUrl.includes('youtube.com/watch?v=') && !youtubeUrl.includes('youtu.be/')) {
        return res.status(400).json({ message: 'Invalid YouTube URL.' });
    }

    const db = await readDb();
    const newVideo = {
        id: db.videos.length + 1,
        title,
        youtubeUrl,
        likes: 0,
        likedBy: [] // Store user IDs who liked this video to prevent duplicate likes
    };
    db.videos.push(newVideo);
    await writeDb(db);
    res.status(201).json({ message: 'Video added successfully!', video: newVideo });
});

// 5. Like a Video (Requires Authentication)
app.post('/api/videos/:id/like', authenticateToken, async (req, res) => {
    const videoId = parseInt(req.params.id);
    const userId = req.user.id; // User ID from authenticated token

    const db = await readDb();
    const video = db.videos.find(v => v.id === videoId);

    if (!video) {
        return res.status(404).json({ message: 'Video not found.' });
    }

    // Check if user has already liked this video
    if (video.likedBy.includes(userId)) {
        return res.status(400).json({ message: 'You have already liked this video.' });
    }

    video.likes += 1;
    video.likedBy.push(userId); // Record that this user liked the video
    await writeDb(db);

    res.json({ message: 'Video liked!', newLikes: video.likes });
});


// Start the server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log('Ensure you have a db.json file in the backend directory, or it will be created.');
});
