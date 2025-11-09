# app.py - Streamlit UI for Gemini Live Assistant (Flask Backend)
import streamlit as st
import requests
import base64
import io
import time
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from PIL import Image

# Flask server URL
FLASK_URL = "http://localhost:5000"

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False

# Page config
st.set_page_config(page_title="Gemini Live Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Gemini Live Assistant")
st.caption("Flask backend + Streamlit UI with browser camera/microphone")

# Info banner
st.info("💡 **Tip:** Start Flask server first: `python flask_server.py`, then allow camera/mic permissions!")

# Layout
col1, col2 = st.columns([0.6, 0.4])

# Video frame callback - sends frames to Flask
def video_callback(frame):
    """Send video frames to Flask server"""
    if st.session_state.is_running and not st.session_state.is_paused:
        try:
            # Convert frame to JPEG
            img = frame.to_image()
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=70)
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode()
            
            # Send to Flask
            requests.post(f"{FLASK_URL}/video", json={"image": img_base64}, timeout=0.1)
        except:
            pass
    return frame

# Audio frame callback - sends audio to Flask
def audio_callback(frame):
    """Send audio frames to Flask server"""
    if st.session_state.is_running and not st.session_state.is_paused:
        try:
            audio_data = frame.to_ndarray().tobytes()
            audio_base64 = base64.b64encode(audio_data).decode()
            
            # Send to Flask
            requests.post(f"{FLASK_URL}/audio", json={"audio": audio_base64}, timeout=0.1)
        except:
            pass
    return frame

with col1:
    st.subheader("Live Camera Feed")
    
    # WebRTC streamer with browser camera
    webrtc_ctx = webrtc_streamer(
        key="gemini-live",
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        media_stream_constraints={"video": True, "audio": True},
        video_frame_callback=video_callback,
        audio_frame_callback=audio_callback,
        async_processing=True,
    )
    
    if webrtc_ctx.state.playing:
        st.success("🎥 Camera and microphone active")
    else:
        st.info("📷 Click START above to activate camera and microphone")

with col2:
    st.subheader("Controls & Transcript")
    
    # Session controls
    if not st.session_state.is_running:
        if st.button("🚀 Start Session", use_container_width=True):
            try:
                response = requests.post(f"{FLASK_URL}/start", timeout=5)
                if response.json().get("status") == "started":
                    st.session_state.is_running = True
                    st.success("Session started!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}. Make sure Flask server is running!")
    else:
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.session_state.is_paused:
                if st.button("▶️ Resume", use_container_width=True):
                    requests.post(f"{FLASK_URL}/resume")
                    st.session_state.is_paused = False
                    st.rerun()
            else:
                if st.button("⏸️ Pause", use_container_width=True):
                    requests.post(f"{FLASK_URL}/pause")
                    st.session_state.is_paused = True
                    st.rerun()
        
        with btn_col2:
            if st.button("🛑 Stop", use_container_width=True):
                requests.post(f"{FLASK_URL}/stop")
                st.session_state.is_running = False
                st.session_state.is_paused = False
                st.session_state.transcript = []
                st.rerun()
        
        # Status
        if st.session_state.is_paused:
            st.warning("⏸️ Session paused")
        else:
            st.success("✅ Session active")
    
    st.markdown("---")
    
    # Transcript display
    st.write("**Conversation:**")
    
    # Fetch transcript from Flask
    if st.session_state.is_running:
        try:
            response = requests.get(f"{FLASK_URL}/transcript", timeout=1)
            transcript = response.json().get("transcript", [])
            st.session_state.transcript = transcript
        except:
            pass
    
    if st.session_state.transcript:
        for entry in st.session_state.transcript:
            st.markdown(entry)
    else:
        st.info("💬 Start a session and speak to see the conversation!")
    
    # Auto-refresh when running
    if st.session_state.is_running:
        time.sleep(1)
        st.rerun()