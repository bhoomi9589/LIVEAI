# ui.py - Streamlit WebRTC UI Component
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

def draw_interface(
    start_session_callback,
    stop_session_callback,
    video_frame_callback,
    audio_frame_callback,
    is_running,
    transcript
):
    """
    Draws the entire Streamlit UI.
    It receives callback functions from app.py to handle logic.
    """
    st.set_page_config(page_title="Gemini Live Assistant", page_icon="🤖", layout="wide")
    st.title("🤖 Gemini Live Assistant")
    st.caption("A real-time multimodal assistant powered by Gemini.")
    
    # Add info banner for Streamlit Cloud
    st.info("💡 **Tip:** Allow camera and microphone permissions when prompted to start chatting with Gemini!")

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.subheader("Live Camera Feed")
        
        try:
            webrtc_ctx = webrtc_streamer(
                key="live-assistant",
                mode=WebRtcMode.SENDONLY, # We only send media to the server
                rtc_configuration=RTCConfiguration(
                    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
                ),
                media_stream_constraints={"video": True, "audio": True},
                video_frame_callback=video_frame_callback,
                audio_frame_callback=audio_frame_callback,
                async_processing=True,
            )
            
            if webrtc_ctx.state.playing:
                st.success("🎥 Camera and microphone active")
            elif webrtc_ctx.state.signalling:
                st.warning("⏳ Connecting to camera...")
            else:
                st.info("📷 Click 'START' below to activate camera and microphone")
                
        except Exception as e:
            st.error(f"❌ WebRTC Error: {str(e)}")
            st.info("Please refresh the page and allow camera/microphone permissions.")

    with col2:
        st.subheader("Controls & Transcript")

        if not is_running:
            if st.button("🚀 Start Session", on_click=start_session_callback, use_container_width=True):
                st.rerun()
        else:
            if st.button("🛑 Stop Session", on_click=stop_session_callback, use_container_width=True):
                st.rerun()

        st.markdown("---")
        
        st.write("**Conversation:**")
        if transcript:
            for entry in transcript:
                st.markdown(entry)
        else:
            st.info("💬 Start a session and speak to see the conversation here!")