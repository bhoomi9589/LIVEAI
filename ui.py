import streamlit as st
import requests
from PIL import Image
import io
import time
import subprocess
import sys

# --- Start Flask Backend ONLY ONCE using Session State ---
if 'backend_process' not in st.session_state:
    st.session_state.backend_process = None

if st.session_state.backend_process is None:
    try:
        print("🚀 Starting Flask backend process for the first time...")
        proc = subprocess.Popen([sys.executable, "app.py"])
        st.session_state.backend_process = proc
        print(f"✅ Flask backend started successfully with PID: {proc.pid}")
    except Exception as e:
        st.error(f"Failed to start Flask backend: {e}")
        st.stop()
# -----------------------------------------------------------

API_URL = "http://127.0.0.1:5000"

def call_api(endpoint, method="GET", data=None, stream=False):
    try:
        url = f"{API_URL}{endpoint}"
        if method == "POST":
            response = requests.post(url, json=data, stream=stream)
        else:
            response = requests.get(url, stream=stream)
        response.raise_for_status()
        if stream:
            return response
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"API connection error: {e}"}

# -----------------------
# Sidebar Controls
# -----------------------
st.sidebar.title("🎛️ Controls")
mode = st.sidebar.radio(
    "Select Mode",
    options=["camera", "screen", "none"],
    index=0,
    help="Choose session mode"
)

if st.sidebar.button("▶️ Start Session"):
    res = call_api("/start", method="POST", data={"mode": mode})
    if res.get("status") == "success":
        st.sidebar.success("✅ Session started")
    else:
        st.sidebar.error(f"❌ {res.get('message', 'Unknown error')}")
    st.rerun()

if st.sidebar.button("⏸️ Pause Session"):
    res = call_api("/pause", method="POST")
    if res.get("status") == "success":
        st.sidebar.info("⏸️ Session paused")
    else:
        st.sidebar.error(f"❌ {res.get('message', 'Unknown error')}")
    st.rerun()

if st.sidebar.button("▶️ Resume Session"):
    res = call_api("/resume", method="POST")
    if res.get("status") == "success":
        st.sidebar.success("▶️ Session resumed")
    else:
        st.sidebar.error(f"❌ {res.get('message', 'Unknown error')}")
    st.rerun()

if st.sidebar.button("🛑 Stop Session"):
    res = call_api("/stop", method="POST")
    if res.get("status") == "success":
        st.sidebar.success("🛑 Session stopped")
    else:
        st.sidebar.error(f"❌ {res.get('message', 'Unknown error')}")
    st.rerun()

# -----------------------
# Main UI
# -----------------------
st.title("🎥 Gemini Live UI")

status_res = call_api("/status")
status_value = status_res.get("status", "error")
mode_value = status_res.get("mode", "none")

st.markdown(f"**Status:** `{status_value.upper()}` | **Mode:** `{mode_value.upper()}`")

image_placeholder = st.empty()

if status_value == "running" and mode_value in ["camera", "screen"]:
    while True:
        frame_response = call_api("/frame", method="GET", stream=True)
        if isinstance(frame_response, dict) and frame_response.get("status") == "error":
            st.error(f"Error fetching frame: {frame_response.get('message')}")
            break
        
        if frame_response and hasattr(frame_response, 'status_code') and frame_response.status_code == 200:
            try:
                img = Image.open(io.BytesIO(frame_response.content))
                image_placeholder.image(img, caption="Live Feed", width='stretch')
            except Exception as e:
                st.error(f"Failed to decode image: {e}")
                break
        else:
            st.warning("Waiting for video stream...")
        
        time.sleep(0.05)
elif status_value == "stopped":
    image_placeholder.info("Session is stopped. Start a new session to see the live feed.")
elif status_value == "paused":
    image_placeholder.info("Session is paused. Resume the session to see the live feed.")