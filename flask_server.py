# flask_server.py - Flask Backend with PyAudio
import os
import asyncio
import io
import pyaudio
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)
CORS(app)

class GeminiSession:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
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
        
        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.audio_stream = None
        
        # Session state
        self.session = None
        self.session_context = None
        self.running = False
        self.paused = False
        self.loop = None
        self.receive_task = None
        self.audio_task = None
        self.transcript = []

    async def start(self):
        """Start Gemini Live session and PyAudio"""
        print("✅ Starting Gemini session...")
        self.running = True
        
        # Start Gemini session
        self.session_context = self.client.aio.live.connect(model=self.model, config=self.config)
        self.session = await self.session_context.__aenter__()
        print("✅ Gemini session connected!")
        
        # Start receive loop
        self.receive_task = asyncio.create_task(self._receive_loop())
        
        # Start PyAudio stream
        self.audio_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024,
            stream_callback=None
        )
        print("🎤 PyAudio stream started")
        
        # Start audio capture task
        self.audio_task = asyncio.create_task(self._audio_capture_loop())
        
        return {"status": "started", "message": "Session connected"}

    async def _receive_loop(self):
        """Listen for Gemini responses"""
        print("🎧 Starting receive loop...")
        try:
            while self.running and self.session:
                try:
                    async for response in self.session.receive():
                        if not self.running:
                            break
                        
                        # Extract text responses
                        if hasattr(response, 'text') and response.text:
                            print(f"📝 Gemini: {response.text}")
                            self.transcript.append(f"🤖 Gemini: {response.text}")
                        
                        if hasattr(response, 'server_content') and response.server_content:
                            if hasattr(response.server_content, 'model_turn'):
                                model_turn = response.server_content.model_turn
                                if hasattr(model_turn, 'parts'):
                                    for part in model_turn.parts:
                                        if hasattr(part, 'text') and part.text:
                                            print(f"📝 Part: {part.text}")
                                            self.transcript.append(f"🤖 Gemini: {part.text}")
                    
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
            print(f"❌ Receive error: {e}")

    async def _audio_capture_loop(self):
        """Capture audio from PyAudio and send to Gemini"""
        print("🎤 Starting audio capture loop...")
        try:
            while self.running and self.audio_stream:
                if not self.paused:
                    try:
                        # Read audio data
                        audio_data = self.audio_stream.read(1024, exception_on_overflow=False)
                        
                        # Send to Gemini
                        if self.session:
                            await self.session.send_realtime_input(
                                media=types.Blob(data=audio_data, mime_type="audio/pcm")
                            )
                    except Exception as e:
                        print(f"⚠️ Audio capture error: {e}")
                
                await asyncio.sleep(0.01)  # Small delay
        except asyncio.CancelledError:
            print("🛑 Audio capture cancelled")
        except Exception as e:
            print(f"❌ Audio capture error: {e}")

    async def stop(self):
        """Stop session and PyAudio"""
        print("🛑 Stopping session...")
        self.running = False
        self.paused = False
        
        # Stop PyAudio stream
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
            print("🎤 PyAudio stream stopped")
        
        # Cancel tasks
        if self.audio_task and not self.audio_task.done():
            self.audio_task.cancel()
            try:
                await self.audio_task
            except asyncio.CancelledError:
                pass
        
        if self.receive_task and not self.receive_task.done():
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        # Close session
        if self.session_context:
            try:
                await self.session_context.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing session: {e}")
            self.session_context = None
        
        self.session = None
        self.transcript = []
        print("🛑 Session stopped")
        return {"status": "stopped", "message": "Session ended"}

    def pause(self):
        """Pause audio capture"""
        if self.running and not self.paused:
            self.paused = True
            print("⏸️ Paused")
            return {"status": "paused"}
        return {"status": "error", "message": "Cannot pause"}

    def resume(self):
        """Resume audio capture"""
        if self.running and self.paused:
            self.paused = False
            print("▶️ Resumed")
            return {"status": "resumed"}
        return {"status": "error", "message": "Cannot resume"}

    async def send_video(self, image_data):
        """Send video frame to Gemini"""
        if not self.running or not self.session or self.paused:
            return
        try:
            await self.session.send_realtime_input(
                media=types.Blob(data=image_data, mime_type="image/jpeg")
            )
        except Exception as e:
            print(f"Error sending video: {e}")

    def get_transcript(self):
        """Get current transcript"""
        return self.transcript

# Global session instance
gemini_session = GeminiSession()

# Flask Routes
@app.route('/start', methods=['POST'])
def start_session():
    """Start Gemini session with PyAudio"""
    try:
        result = asyncio.run(gemini_session.start())
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_session():
    """Stop Gemini session"""
    try:
        result = asyncio.run(gemini_session.stop())
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/pause', methods=['POST'])
def pause_session():
    """Pause session"""
    result = gemini_session.pause()
    return jsonify(result)

@app.route('/resume', methods=['POST'])
def resume_session():
    """Resume session"""
    result = gemini_session.resume()
    return jsonify(result)

@app.route('/video', methods=['POST'])
def send_video():
    """Receive video frame from Streamlit"""
    try:
        import base64
        data = request.json
        image_base64 = data.get('image')
        if not image_base64:
            return jsonify({"status": "error", "message": "No image data"}), 400
        
        image_data = base64.b64decode(image_base64)
        asyncio.run(gemini_session.send_video(image_data))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/transcript', methods=['GET'])
def get_transcript():
    """Get current transcript"""
    transcript = gemini_session.get_transcript()
    return jsonify({"transcript": transcript})

@app.route('/status', methods=['GET'])
def get_status():
    """Get session status"""
    return jsonify({
        "running": gemini_session.running,
        "paused": gemini_session.paused
    })

if __name__ == '__main__':
    print("🚀 Starting Flask server with PyAudio on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
