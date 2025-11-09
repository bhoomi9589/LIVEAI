# live.py - Gemini Live Backend Logic
import os
import asyncio
import io
import av
from PIL import Image

from google import genai
from google.genai import types

class GeminiLive:
    """
    Manages all backend logic for the Gemini LiveConnect session.
    This class is completely independent of Streamlit or Flask.
    """
    def __init__(self):
        # --- Gemini API Setup ---
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # First, check for Streamlit secrets
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except (ImportError, AttributeError):
                pass
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file or Streamlit secrets.")
        
        # Create the client with the API key
        self.client = genai.Client(api_key=api_key)

        # Use a model that supports live/bidirectional streaming
        self.model = "models/gemini-2.0-flash-live-001"
        self.tools = [types.Tool(google_search=types.GoogleSearch())]
        self.config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO], # Model can respond with audio
            generation_config=types.GenerationConfig(max_output_tokens=300, temperature=0.7),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")
                )
            ),
            tools=types.ToolListUnion(self.tools),
        )
        self.session = None
        self.session_context = None
        self.running = False
        self.paused = False
        self.receive_task = None
        self.ui_callback = None

    async def start_session(self):
        """Starts a new Gemini LiveConnect session."""
        print("✅ Starting Gemini session...")
        self.running = True
        # Store the async context manager
        self.session_context = self.client.aio.live.connect(model=self.model, config=self.config)
        # Enter the context and get the session
        self.session = await self.session_context.__aenter__()
        print("✅ Session connected!")
        
        # Start the background receive task if callback is set
        if self.ui_callback:
            self.receive_task = asyncio.create_task(self._receive_loop())
            print("🎧 Started receive loop")

    async def _receive_loop(self):
        """Background task that continuously listens for responses."""
        print("🎧 Starting background receive loop...")
        try:
            while self.running and self.session:
                try:
                    # This will block until there's a response
                    async for response in self.session.receive():
                        if not self.running:
                            break
                        
                        # Process the response
                        if hasattr(response, 'text') and response.text:
                            print(f"📝 Received text: {response.text}")
                            if self.ui_callback:
                                self.ui_callback("text", response.text)
                        
                        if hasattr(response, 'server_content') and response.server_content:
                            if hasattr(response.server_content, 'model_turn'):
                                model_turn = response.server_content.model_turn
                                if hasattr(model_turn, 'parts'):
                                    for part in model_turn.parts:
                                        if hasattr(part, 'text') and part.text:
                                            print(f"📝 Part text: {part.text}")
                                            if self.ui_callback:
                                                self.ui_callback("text", part.text)
                        
                        if hasattr(response, 'parts'):
                            for part in response.parts:
                                if hasattr(part, 'tool_call') and part.tool_call:
                                    print(f"🔧 Tool call: {part.tool_call.name}")
                                    if self.ui_callback:
                                        self.ui_callback("tool", f"[🛠️ Tool Call: {part.tool_call.name}]")
                    
                    # If receive() completes, wait before trying again
                    await asyncio.sleep(1.0)
                
                except Exception as e:
                    if self.running:
                        # Only log errors if session is still supposed to be running
                        error_msg = str(e)
                        if "1000" not in error_msg:  # Don't log normal WebSocket closures
                            print(f"⚠️ Receive error: {e}")
                        await asyncio.sleep(1.0)
                    else:
                        break
                        
        except asyncio.CancelledError:
            print("🛑 Receive loop cancelled")
        except Exception as e:
            print(f"❌ Fatal receive error: {e}")
        finally:
            print("🎧 Receive loop stopped")

    async def stop_session(self):
        """Stops the current Gemini LiveConnect session."""
        print("🛑 stop_session() called")
        self.running = False
        self.paused = False
        
        # Cancel the receive task if it's running
        if self.receive_task and not self.receive_task.done():
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        if self.session_context:
            try:
                await self.session_context.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing session: {e}")
            self.session_context = None
        
        self.session = None
        self.receive_task = None
        print("🛑 Gemini session stopped.")

    def pause_session(self):
        """Pauses the current session (stops sending frames but keeps connection alive)."""
        if self.running and not self.paused:
            self.paused = True
            print("⏸️ Session paused")
            return True
        return False

    def resume_session(self):
        """Resumes a paused session."""
        if self.running and self.paused:
            self.paused = False
            print("▶️ Session resumed")
            return True
        return False

    async def send_audio_frame(self, frame: av.AudioFrame):
        """Processes and sends an audio frame from WebRTC to Gemini."""
        if not self.running or not self.session or self.paused:
            return
        audio_data = frame.to_ndarray().tobytes()
        try:
            await self.session.send_realtime_input(
                media=types.Blob(data=audio_data, mime_type="audio/pcm")
            )
        except Exception as e:
            print(f"Error sending audio: {e}")

    async def send_video_frame(self, frame: av.VideoFrame):
        """Processes and sends a video frame from WebRTC to Gemini."""
        if not self.running or not self.session or self.paused:
            return

        img = frame.to_image()
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        
        # Note: 'data' for image blobs should be raw bytes, not base64 encoded string
        # for this specific API endpoint.
        image_data = image_io.getvalue()
        try:
            await self.session.send_realtime_input(
                media=types.Blob(data=image_data, mime_type="image/jpeg")
            )
        except Exception as e:
            print(f"Error sending video frame: {e}")

    def receive_responses(self, ui_callback):
        """Sets up the UI callback for receiving responses."""
        self.ui_callback = ui_callback
        print(f"✅ UI callback registered")