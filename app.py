# app.py - Streamlit UI with Direct Gemini Connection
import streamlit as st
import asyncio
from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from live import GeminiLive

load_dotenv()

# Initialize GeminiLive
if 'gemini_live' not in st.session_state:
    try:
        st.session_state.gemini_live = GeminiLive()
    except ValueError as e:
        st.error(str(e))
        st.stop()

# Initialize paused attribute for backward compatibility
if not hasattr(st.session_state.gemini_live, 'paused'):
    st.session_state.gemini_live.paused = False

# Initialize session state
if 'transcript' not in st.session_state:
    st.session_state.transcript = []

# Callback functions
def start_session_callback():
    """Start Gemini session"""
    if not st.session_state.gemini_live.ui_callback:
        st.session_state.gemini_live.receive_responses(ui_update_callback)
    asyncio.run(st.session_state.gemini_live.start_session())

def stop_session_callback():
    """Stop Gemini session"""
    asyncio.run(st.session_state.gemini_live.stop_session())
    st.session_state.transcript = []

def pause_session_callback():
    """Pause Gemini session"""
    if hasattr(st.session_state.gemini_live, 'pause_session'):
        st.session_state.gemini_live.pause_session()
    else:
        st.session_state.gemini_live.paused = True

def resume_session_callback():
    """Resume Gemini session"""
    if hasattr(st.session_state.gemini_live, 'resume_session'):
        st.session_state.gemini_live.resume_session()
    else:
        st.session_state.gemini_live.paused = False

def ui_update_callback(event_type, data):
    """Update UI with Gemini responses"""
    if event_type == "error":
        st.error(data)
    elif event_type == "text":
        st.session_state.transcript.append(f"**🤖 Gemini:** {data}")
    elif event_type == "tool":
        st.session_state.transcript.append(f"*{data}*")
    
    if 'rerun_needed' not in st.session_state:
        st.session_state.rerun_needed = True

# Check if rerun needed
if st.session_state.get('rerun_needed', False):
    st.session_state.rerun_needed = False
    st.rerun()

# Page config
st.set_page_config(page_title="Gemini Live Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Gemini Live Assistant")
st.caption("Real-time multimodal AI with browser camera/microphone")

st.info("💡 **Tip:** Allow camera and microphone permissions to start chatting with Gemini!")

# Layout
col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.subheader("📹 Live Camera Feed")
    
    # WebRTC streamer
    webrtc_ctx = webrtc_streamer(
        key="gemini-live",
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        media_stream_constraints={"video": True, "audio": True},
        video_frame_callback=st.session_state.gemini_live.send_video_frame,
        audio_frame_callback=st.session_state.gemini_live.send_audio_frame,
        async_processing=True,
    )
    
    if webrtc_ctx.state.playing:
        st.success("🎥 Camera and microphone active")
    else:
        st.info("📷 Click START above to activate camera and microphone")

with col2:
    st.subheader("🎛️ Controls & Transcript")
    
    # Session controls
    if not st.session_state.gemini_live.running:
        if st.button("🚀 Start Session", on_click=start_session_callback, use_container_width=True):
            st.rerun()
    else:
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.session_state.gemini_live.paused:
                if st.button("▶️ Resume", on_click=resume_session_callback, use_container_width=True):
                    st.rerun()
            else:
                if st.button("⏸️ Pause", on_click=pause_session_callback, use_container_width=True):
                    st.rerun()
        
        with btn_col2:
            if st.button("🛑 Stop", on_click=stop_session_callback, use_container_width=True):
                st.rerun()
        
        # Status
        if st.session_state.gemini_live.paused:
            st.warning("⏸️ Session paused - Click Resume to continue")
        else:
            st.success("✅ Session active - Speak to Gemini!")
    
    st.markdown("---")
    
    # Transcript display
    st.write("**💬 Conversation:**")
    
    if st.session_state.transcript:
        for entry in st.session_state.transcript:
            st.markdown(entry)
    else:
        st.info("💭 Start a session and speak to see the conversation here!")
