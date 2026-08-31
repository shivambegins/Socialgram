# Socialgram ✨

Socialgram is a modern, real-time social media web application built with **Django**, **Django Channels**, and **WebSockets**. It features a beautiful dark-mode UI inspired by the latest design trends (glassmorphism, clean typography) and includes advanced real-time communication capabilities like live messaging, instant notifications, and WebRTC video/voice calling.

## 🚀 Features

### Core Social Features
- **User Authentication:** Secure signup, login, and robust password reset flow via real SMTP email.
- **Custom Profiles:** Upload avatars, write bios, update locations, and view activity stats.
- **Posts & Feed:** Create posts with images and captions. The home feed intelligently filters out blocked users and prioritizes relevant content.
- **Interactions:** Like posts, leave comments, and share content seamlessly.
- **Connections:** Connect with friends and build your network.

### ⚡ Real-Time Capabilities (WebSockets & Channels)
- **Live 1-on-1 Messaging:** Send and receive messages instantly without refreshing the page.
- **Group Chats:** Create dynamic group conversations.
- **WebRTC Video & Voice Calls:** High-quality peer-to-peer video and audio calling right in the browser, featuring a seamless toggle between voice and video modes, and call-merging functionality.
- **Instant Notifications:** Get live toast notifications when someone likes your post, comments, sends a message, or calls you.

### 🛡️ Advanced Settings & Privacy
- **Screen Time Tracker:** A live, background JavaScript tracker that calculates exactly how many active minutes you spend on the app, visualized with a beautifully rendered 7-day Chart.js graph.
- **Account Management:** Securely delete your account verified via an emailed 6-digit One-Time Password (OTP).
- **User Blocking:** Block unwanted users. Blocked users are automatically removed from your connections, and their content is hidden from your feed.

## 🛠️ Tech Stack

- **Backend:** Python, Django 6.1, Django Channels (WebSockets for real-time functionality)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Chart.js (for Screen Time analytics)
- **Real-Time Video/Audio:** WebRTC
- **Database:** SQLite (default for development), configurable for PostgreSQL.
- **Authentication:** Django Auth, `python-dotenv` for managing environment variables (like SMTP credentials).

## 💻 Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/shivambegins/Socialgram.git
cd Socialgram
```

### 2. Create and activate a Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory (same level as `manage.py`) and add your SMTP credentials for password resets and OTP emails:
```env
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_character_app_password
```

### 5. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Start the Development Server
Because this app relies heavily on WebSockets, it runs via an ASGI server. 
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser!

---


