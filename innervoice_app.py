import streamlit as st
import cv2
from deepface import DeepFace
import pyttsx3
import tempfile
import os
import time
import pandas as pd
import calendar
from datetime import datetime
from pymongo import MongoClient
import uuid

# Set up Streamlit page configuration
st.set_page_config(page_title="InnerVoice", layout="wide")

# ------------------- MONGODB SETUP -------------------
client = MongoClient("mongodb://localhost:27017/")
db = client.innervoice_app
users_collection = db.users
moods_collection = db.moods

# ------------------- SESSION STATE -------------------
def init_session():
    defaults = {
        'current_user': None,
        'logged_in': False,
        'page': 'Welcome',
        'chat_history': [],
        'chat_stage': '',
        'chat_mood': '',
        'chat_topic': '',
        'camera_on': False,
        'image_captured': False,
        'preview_active': False,
        'captured_frame': None,
        'ready_to_capture_clicked': False,
        'capture_now': False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ------------------- NAVIGATION BAR -------------------
def navigation():
    if not st.session_state['current_user']:
        nav_links = ["Welcome", "About Us", "Login/Signup"]
    else:
        nav_links = ["Home", "About Us", "Your Tools", "Profile"]

    st.markdown("""
        <style>
        .nav-container {
            display: flex;
            justify-content: center;
            gap: 40px;
            background-color: #111;
            padding: 15px;
        }
        .nav-button {
            font-size: 18px;
            color: white;
            font-weight: bold;
            background: none;
            border: none;
            cursor: pointer;
        }
        .nav-button:hover {
            color: #00f2ff;
        }
        </style>
        <div class="nav-container">
    """, unsafe_allow_html=True)
    cols = st.columns(len(nav_links))
    for i, link in enumerate(nav_links):
        if cols[i].button(link, key=f"nav_{link}"):
            st.session_state['page'] = link if link != "Login/Signup" else "Login"
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------- PAGES -------------------
def welcome():
    st.markdown("""
        <style>
            .welcome-container {
                text-align: center;
                padding-top: 100px;
                background-image: url('https://images.unsplash.com/photo-1506744038136-46273834b3fb');
                background-size: cover;
                height: 90vh;
            }
            .welcome-title {
                font-size: 64px;
                color: white;
                font-weight: bold;
            }
            .welcome-subtitle {
                font-size: 24px;
                color: #eeeeee;
                margin-top: 10px;
            }
        </style>
        <div class="welcome-container">
            <div class="welcome-title">Inner Voice</div>
            <div class="welcome-subtitle">Helping you understand and express your emotions</div>
        </div>
    """, unsafe_allow_html=True)

def home():
    welcome()

def login():
    st.header("Login or Sign Up")
    choice = st.radio("Choose one:", ["Login", "Sign Up"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Submit"):
        if choice == "Sign Up":
            if users_collection.find_one({"username": username}):
                st.error("Username already exists.")
            else:
                users_collection.insert_one({"username": username, "password": password})
                st.success("Account created! Please log in.")
        elif choice == "Login":
            user = users_collection.find_one({"username": username, "password": password})
            if user:
                st.session_state['current_user'] = username
                st.session_state['logged_in'] = True
                st.success(f"Welcome back, {username}!")
                st.session_state['page'] = 'Home'
            else:
                st.error("Invalid credentials.")

def about():
    st.header("About InnerVoice")
    st.write("""
    InnerVoice is designed to help neurodivergent and disabled users gain control over their emotional world. 
    By combining emotion detection, guided reflection, and coping tools, we make communication easier — even when words are hard to find.
    """)

def profile():
    st.header("👤 Your Profile")
    if st.session_state['current_user']:
        st.write(f"Hello, **{st.session_state['current_user']}** 👋")
        st.subheader("Your Mood History")
        user_logs = list(moods_collection.find({"username": st.session_state['current_user']}))
        if user_logs:
            df = pd.DataFrame(user_logs)
            df = df.drop(columns=['_id'])
            st.dataframe(df.sort_values(by="date", ascending=False))
        else:
            st.info("You haven't logged any moods yet.")
    else:
        st.warning("Please log in to view your profile.")

def tools():
    st.header("🧰 Your Tools")
    st.write("Access tools to help you reflect and grow.")

    tab1, tab2, tab3, tab4 = st.tabs(["Breathwork", "Emotion Detector", "ChatBot", "Mood Calendar"])

    with tab1:
        st.subheader("Breathwork")
        st.write("Try a simple breathing exercise: Inhale for 4 seconds, hold for 4, exhale for 4. 💨")

    with tab2:
        st.subheader("Emotion Detector")
        st.write("Click below to capture your emotion instantly.")
        if st.button("Detect Emotion"):
            cap = cv2.VideoCapture(0)
            time.sleep(2)  # Let camera warm up
            for _ in range(15):
                ret, frame = cap.read()
                if not ret:
                    break
            cap.release()
            if not ret:
                st.error("Could not access webcam. Please try again.")
            else:
                # Enhance brightness and contrast
                enhanced = cv2.convertScaleAbs(frame, alpha=1.2, beta=30)
                img_path = os.path.join(tempfile.gettempdir(), "captured.jpg")
                cv2.imwrite(img_path, enhanced)
                st.image(enhanced, caption="Captured Image", channels="BGR", use_container_width=True)
                try:
                    result = DeepFace.analyze(img_path=img_path, actions=['emotion'], enforce_detection=True)
                    emotion = result[0].get('dominant_emotion') if isinstance(result, list) else result.get('dominant_emotion')
                    if emotion:
                        st.success(f"Detected emotion: {emotion}")
                    else:
                        st.error("No dominant emotion found. Try again with more facial expression.")
                except Exception as e:
                    st.error("No face or emotion could be clearly detected. Please try again.")

    with tab3:
        st.subheader("ChatBot")
        user_input = st.text_input("You:")
        if user_input:
            st.session_state.chat_history.append(("You", user_input))
            response = ""
            if any(word in user_input.lower() for word in ["happy", "excited", "joy"]):
                response = "That's wonderful to hear! How does your body feel when you're happy?"
            elif any(word in user_input.lower() for word in ["sad", "tired", "down"]):
                response = "I'm really sorry you're feeling that way. What do you think triggered it today?"
            elif any(word in user_input.lower() for word in ["angry", "mad", "upset"]):
                response = "It sounds like something's bothering you. Want to talk about it?"
            elif any(word in user_input.lower() for word in ["coping", "strategy", "breathe"]):
                response = "Which one would you like to try: breathwork, journaling, or talking to someone you trust?"
            elif any(word in user_input.lower() for word in ["breathwork", "breathing"]):
                response = "Try a simple breathing exercise: Inhale for 4, hold for 4, exhale for 4. 💨"
            elif "journal" in user_input.lower():
                response = "Open up your notes or journal and just let the thoughts flow. ✍️"
            elif any(word in user_input.lower() for word in ["talk", "friend"]):
                response = "Consider calling a friend or someone you trust. You're not alone. 📞"
            else:
                response = "Thanks for sharing. Would you like to explore coping strategies or keep talking?"
            st.session_state.chat_history.append(("Bot", response))
        for speaker, msg in st.session_state.chat_history:
            st.write(f"**{speaker}:** {msg}")

    with tab4:
        st.subheader("Mood Calendar")
        now = datetime.now()
        today = now.strftime("%Y-%m-%d %H:%M:%S")
        mood = st.selectbox("Log in the mood for " + today, ["😀 Happy", "😔 Sad", "😠 Angry", "😨 Anxious", "😌 Calm"])
        if st.button("Log Mood"):
            moods_collection.insert_one({
                "username": st.session_state['current_user'],
                "date": today,
                "mood": mood
            })
            st.success("Mood logged!")
        st.write("### Your Mood Log")
        mood_entries = list(moods_collection.find({"username": st.session_state['current_user']}))
        if mood_entries:
            mood_entries.sort(key=lambda x: x['date'], reverse=True)
            formatted_entries = [f"{entry['date']}: {entry['mood']}" for entry in mood_entries]
            delete_target = st.selectbox("Select an entry to delete", formatted_entries)
            if st.button("Delete Selected Entry"):
                target_date = delete_target.split(":")[0]
                moods_collection.delete_one({"username": st.session_state['current_user'], "date": target_date})
                st.success("Mood entry deleted!")
                st.rerun()

# ------------------- ROUTING -------------------
navigation()
page = st.session_state['page']
if page == "Welcome":
    welcome()
elif page == "Home":
    home()
elif page == "Login":
    login()
elif page == "About Us":
    about()
elif page == "Your Tools":
    tools()
elif page == "Profile":
    profile()
