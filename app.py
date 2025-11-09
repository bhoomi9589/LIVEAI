# app.py - Streamlit UI with PyAudio System Audio
import streamlit as st
import threading
import time
import queue
from dotenv import load_dotenv
from live import GeminiLive

load_dotenv()

# Module-level queue for thread-safe communication (not in session_state!)
MESSAGE_QUEUE = queue.Queue()

# Initialize session state
if 'gemini_live' not in st.session_state:
    try:
        st.session_state.gemini_live = GeminiLive()
    except ValueError as e:
        st.error(str(e))
        st.stop()

if 'transcript' not in st.session_state:
    st.session_state.transcript = []

if 'session_thread' not in st.session_state:
    st.session_state.session_thread = None

# Callback to update UI (thread-safe with module-level queue)
def ui_update_callback(event_type, data):
    """Update UI with Gemini responses - thread-safe"""
    try:
        MESSAGE_QUEUE.put((event_type, data))
    except Exception as e:
        print(f"Error adding message to queue: {e}")

# Process messages from queue
def process_messages():
    """Process all messages from the queue"""
    try:
        while not MESSAGE_QUEUE.empty():
            event_type, data = MESSAGE_QUEUE.get_nowait()
            
            if event_type == "error":
                st.session_state.transcript.append(f"❌ **Error:** {data}")
            elif event_type == "text":
                st.session_state.transcript.append(f"**🤖 Gemini:** {data}")
            elif event_type == "tool":
                st.session_state.transcript.append(f"*🔧 {data}*")
    except queue.Empty:
        pass
    except Exception as e:
        print(f"Error processing messages: {e}")

# Session control functions
def start_session():
    """Start Gemini Live session in background thread"""
    def run_session(gemini_instance, callback):
        """Run the session with passed instances - no session_state access"""
        gemini_instance.ui_callback = callback
        import asyncio
        try:
            asyncio.run(gemini_instance.start_session())
        except Exception as e:
            print(f"Session error: {e}")
            callback("error", str(e))
    
    if not st.session_state.gemini_live.running:
        st.session_state.session_thread = threading.Thread(
            target=run_session, 
            args=(st.session_state.gemini_live, ui_update_callback),
            daemon=True
        )
        st.session_state.session_thread.start()
        time.sleep(0.5)  # Give it time to start

def stop_session():
    """Stop Gemini Live session"""
    if st.session_state.gemini_live.running:
        # Mark as not running first
        st.session_state.gemini_live.running = False
        st.session_state.gemini_live.paused = False
        
        # Give threads time to notice the stop
        time.sleep(0.5)
        
        # Clean up resources synchronously
        if st.session_state.gemini_live.camera:
            st.session_state.gemini_live.camera_running = False
            try:
                st.session_state.gemini_live.camera.release()
                st.session_state.gemini_live.camera = None
            except:
                pass
        
        if st.session_state.gemini_live.audio_stream:
            try:
                st.session_state.gemini_live.audio_stream.stop_stream()
                st.session_state.gemini_live.audio_stream.close()
                st.session_state.gemini_live.audio_stream = None
            except:
                pass
        
        st.session_state.gemini_live.latest_frame = None
        st.session_state.transcript = []
        st.session_state.session_thread = None
        
        # Clear the module-level message queue
        while not MESSAGE_QUEUE.empty():
            MESSAGE_QUEUE.get()

def pause_session():
    """Pause Gemini Live session"""
    st.session_state.gemini_live.pause_session()

def resume_session():
    """Resume Gemini Live session"""
    st.session_state.gemini_live.resume_session()

# Page config
st.set_page_config(page_title="Gemini Live Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Gemini Live Assistant")
st.caption("Real-time multimodal AI with system audio and camera")

st.info("💡 **System Audio Capture:** This app uses PyAudio to capture system microphone and camera feed.")

# Process messages from queue before rendering UI
process_messages()

# Layout
col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.subheader("📹 Camera Feed")
    
    # Camera placeholder
    camera_placeholder = st.empty()
    
    # Show latest frame if available
    if st.session_state.gemini_live.latest_frame is not None:
        camera_placeholder.image(
            st.session_state.gemini_live.latest_frame, 
            caption="Live Camera Feed", 
            use_container_width=True
        )
    else:
        # Show status message
        if st.session_state.gemini_live.running:
            if st.session_state.gemini_live.camera_running:
                camera_placeholder.info("📷 Camera is initializing... waiting for first frame")
            else:
                camera_placeholder.warning("⚠️ Camera not available (no hardware detected on server)")
        else:
            camera_placeholder.info("📷 Camera will activate when you start the session")
    
    # Display status
    if st.session_state.gemini_live.running:
        if st.session_state.gemini_live.camera_running:
            st.success("🎥 Camera capture active")
        else:
            st.warning("⚠️ No camera hardware detected")
        st.info("🎤 Microphone capture active (PyAudio)")
    else:
        st.caption("💡 Click 'Start Session' to activate camera and microphone")

with col2:
    st.subheader("🎛️ Controls & Transcript")
    
    # Session controls
    if not st.session_state.gemini_live.running:
        if st.button("🚀 Start Session", use_container_width=True):
            start_session()
            time.sleep(1)
            st.rerun()
    else:
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.session_state.gemini_live.paused:
                if st.button("▶️ Resume", use_container_width=True):
                    resume_session()
                    st.rerun()
            else:
                if st.button("⏸️ Pause", use_container_width=True):
                    pause_session()
                    st.rerun()
        
        with btn_col2:
            if st.button("🛑 Stop", use_container_width=True):
                stop_session()
                st.rerun()
        
        # Status
        if st.session_state.gemini_live.paused:
            st.warning("⏸️ Session paused - Click Resume to continue")
        else:
            st.success("✅ Session active - Speak to Gemini!")
    
    st.markdown("---")
    
    # Transcript display
    st.write("**💬 Conversation:**")
    
    transcript_container = st.container()
    with transcript_container:
        if st.session_state.transcript:
            for entry in st.session_state.transcript[-20:]:  # Show last 20 messages
                st.markdown(entry)
        else:
            st.info("💭 Start a session and speak to see the conversation here!")

# Auto-refresh while session is running (reduced frequency to lower server load)
if st.session_state.gemini_live.running:
    time.sleep(1.0)  # Changed from 0.5 to 1.0 second
    st.rerun()
