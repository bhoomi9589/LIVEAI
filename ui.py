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

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.subheader("Live Camera Feed")
        webrtc_streamer(
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

    with col2:
        st.subheader("Controls & Transcript")

        if not is_running:
            st.button("🚀 Start Session", on_click=start_session_callback, use_container_width=True)
        else:
            st.button("🛑 Stop Session", on_click=stop_session_callback, use_container_width=True)

        st.markdown("---")
        
        transcript_placeholder = st.empty()
        with transcript_placeholder.container():
            st.write("**Conversation:**")
            for entry in transcript:
                st.markdown(entry)