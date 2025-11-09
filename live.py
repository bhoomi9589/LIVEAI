# live.py - Gemini Live Backend Logic (No Flask)
import os
import asyncio
import io
from google import genai
from google.genai import types

class GeminiLive:
    """
    Manages Gemini Live session directly in Streamlit.
    No Flask server needed - browser camera sends directly to Gemini.
    """
    def __init__(self):
        # Get API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except:
                pass
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file or Streamlit secrets")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-2.0-flash-live-001"
        self.tools = [types.Tool(google_search=types.GoogleSearch())]
        self.config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
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
        """Start Gemini Live session"""
        print("✅ Starting Gemini session...")
        self.running = True
        self.session_context = self.client.aio.live.connect(model=self.model, config=self.config)
        self.session = await self.session_context.__aenter__()
        print("✅ Session connected!")
        
        if self.ui_callback:
            self.receive_task = asyncio.create_task(self._receive_loop())
            print("🎧 Started receive loop")

    async def _receive_loop(self):
        """Listen for Gemini responses"""
        print("🎧 Starting background receive loop...")
        try:
            while self.running and self.session:
                try:
                    async for response in self.session.receive():
                        if not self.running:
                            break
                        
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
                    
                    await asyncio.sleep(1.0)
                
                except Exception as e:
                    if self.running:
                        error_msg = str(e)
                        if "1000" not in error_msg:
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
        """Stop Gemini Live session"""
        print("🛑 Stopping session...")
        self.running = False
        self.paused = False
        
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
        print("🛑 Session stopped")

    def pause_session(self):
        """Pause session"""
        if self.running and not self.paused:
            self.paused = True
            print("⏸️ Session paused")
            return True
        return False

    def resume_session(self):
        """Resume session"""
        if self.running and self.paused:
            self.paused = False
            print("▶️ Session resumed")
            return True
        return False

    async def send_audio_frame(self, frame):
        """Send audio frame to Gemini"""
        if not self.running or not self.session or self.paused:
            return
        try:
            audio_data = frame.to_ndarray().tobytes()
            await self.session.send_realtime_input(
                media=types.Blob(data=audio_data, mime_type="audio/pcm")
            )
        except Exception as e:
            print(f"Error sending audio: {e}")

    async def send_video_frame(self, frame):
        """Send video frame to Gemini"""
        if not self.running or not self.session or self.paused:
            return
        try:
            img = frame.to_image()
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=70)
            image_data = img_byte_arr.getvalue()
            
            await self.session.send_realtime_input(
                media=types.Blob(data=image_data, mime_type="image/jpeg")
            )
        except Exception as e:
            print(f"Error sending video: {e}")

    def receive_responses(self, ui_callback):
        """Set UI callback for responses"""
        self.ui_callback = ui_callback
        print("✅ UI callback registered")

