# live.py - Gemini Live Backend with PyAudio
import os
import asyncio
import io
import numpy as np
from PIL import Image
from google import genai
from google.genai import types

# Try importing PyAudio - may not be available on all platforms
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("⚠️ PyAudio not available - audio capture disabled")

class GeminiLive:
    """
    Manages Gemini Live session with PyAudio for system audio capture.
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
        
        # PyAudio setup
        if PYAUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
        else:
            self.audio = None
        self.audio_stream = None
        self.audio_task = None
        self.event_loop = None  # Store the asyncio event loop
        
        # Camera setup
        self.camera = None
        self.camera_running = False
        self.latest_frame = None
        self.camera_task = None

    async def start_session(self):
        """Start Gemini Live session"""
        print("✅ Starting Gemini session...")
        self.running = True
        self.event_loop = asyncio.get_event_loop()  # Store the event loop
        self.session_context = self.client.aio.live.connect(model=self.model, config=self.config)
        self.session = await self.session_context.__aenter__()
        print("✅ Session connected!")
        
        if self.ui_callback:
            self.receive_task = asyncio.create_task(self._receive_loop())
            print("🎧 Started receive loop")
        
        # Start PyAudio capture
        self.start_audio_capture()
        
        # Start camera capture
        self.start_camera_capture()

    def start_audio_capture(self):
        """Start capturing audio from microphone using PyAudio"""
        if not PYAUDIO_AVAILABLE or not self.audio:
            print("⚠️ PyAudio not available - skipping audio capture")
            return
        
        try:
            self.audio_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            self.audio_stream.start_stream()
            print("🎤 PyAudio microphone started")
        except Exception as e:
            print(f"❌ PyAudio error: {e}")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback - sends audio to Gemini"""
        if self.running and self.session and not self.paused and self.event_loop:
            try:
                # Send audio data to Gemini using the stored event loop
                asyncio.run_coroutine_threadsafe(
                    self.session.send_realtime_input(
                        media=types.Blob(data=in_data, mime_type="audio/pcm")
                    ),
                    self.event_loop
                )
            except Exception as e:
                print(f"Error sending audio: {e}")
        return (in_data, pyaudio.paContinue)

    def start_camera_capture(self):
        """Start capturing frames from camera using OpenCV"""
        try:
            import cv2
            self.camera = cv2.VideoCapture(0)
            
            # Give camera time to initialize
            import time
            time.sleep(0.5)
            
            if self.camera.isOpened():
                # Test if we can actually read a frame
                ret, test_frame = self.camera.read()
                if ret:
                    self.camera_running = True
                    print("📷 Camera started successfully")
                    # Start camera loop in background
                    import threading
                    threading.Thread(target=self._camera_loop, daemon=True).start()
                else:
                    print("⚠️ Camera opened but can't read frames - likely no hardware")
                    self.camera.release()
                    self.camera = None
                    self._create_placeholder_frame()
            else:
                print("⚠️ No camera hardware detected")
                self.camera = None
                self._create_placeholder_frame()
        except Exception as e:
            print(f"❌ Camera error: {e}")
            self.camera = None
            self._create_placeholder_frame()
    
    def _create_placeholder_frame(self):
        """Create a placeholder image when no camera is available"""
        try:
            import numpy as np
            # Create a simple placeholder image
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add text-like pattern
            placeholder[200:280, 150:490] = [40, 40, 60]
            self.latest_frame = placeholder
            print("📷 Created placeholder frame (no camera hardware)")
        except Exception as e:
            print(f"Error creating placeholder: {e}")
    
    def _camera_loop(self):
        """Continuously capture and send camera frames"""
        import cv2
        while self.running and self.camera_running:
            if self.paused:
                continue
            
            try:
                ret, frame = self.camera.read()
                if ret:
                    # Store latest frame for UI display
                    self.latest_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Send frame to Gemini every 1 second (adjust as needed)
                    if self.session and self.event_loop:
                        # Resize for efficiency
                        small_frame = cv2.resize(frame, (640, 480))
                        _, buffer = cv2.imencode('.jpg', small_frame)
                        
                        # Send to Gemini using stored event loop
                        try:
                            asyncio.run_coroutine_threadsafe(
                                self.session.send_realtime_input(
                                    media=types.Blob(data=buffer.tobytes(), mime_type="image/jpeg")
                                ),
                                self.event_loop
                            )
                        except Exception as e:
                            print(f"Error sending frame: {e}")
                
                # Throttle to ~1 fps for camera
                import time
                time.sleep(1.0)
            except Exception as e:
                print(f"Camera capture error: {e}")
                break

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
        
        # Stop camera
        if self.camera:
            self.camera_running = False
            self.camera.release()
            self.camera = None
            self.latest_frame = None
            print("📷 Camera stopped")
        
        # Stop PyAudio
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
            print("🎤 PyAudio stopped")
        
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

    async def send_video_frame(self, frame_data):
        """Send video frame to Gemini (for webcam if needed)"""
        if not self.running or not self.session or self.paused:
            return
        try:
            await self.session.send_realtime_input(
                media=types.Blob(data=frame_data, mime_type="image/jpeg")
            )
        except Exception as e:
            print(f"Error sending video: {e}")

    def receive_responses(self, ui_callback):
        """Set UI callback for responses"""
        self.ui_callback = ui_callback
        print("✅ UI callback registered")
    
    def __del__(self):
        """Cleanup PyAudio on deletion"""
        if PYAUDIO_AVAILABLE and hasattr(self, 'audio') and self.audio:
            self.audio.terminate()

