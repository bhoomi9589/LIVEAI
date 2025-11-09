# live.py - Helper functions for communicating with Flask backend
import requests
import base64
import io

FLASK_URL = "http://localhost:5000"

class FlaskClient:
    """Client to communicate with Flask backend"""
    
    def __init__(self):
        self.flask_url = FLASK_URL
    
    def start_session(self):
        """Start Gemini session on Flask backend"""
        try:
            response = requests.post(f"{self.flask_url}/start", timeout=5)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def stop_session(self):
        """Stop Gemini session on Flask backend"""
        try:
            response = requests.post(f"{self.flask_url}/stop", timeout=5)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def pause_session(self):
        """Pause Gemini session"""
        try:
            response = requests.post(f"{self.flask_url}/pause", timeout=2)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def resume_session(self):
        """Resume Gemini session"""
        try:
            response = requests.post(f"{self.flask_url}/resume", timeout=2)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def send_audio(self, audio_data):
        """Send audio data to Flask backend"""
        try:
            audio_base64 = base64.b64encode(audio_data).decode()
            requests.post(
                f"{self.flask_url}/audio", 
                json={"audio": audio_base64}, 
                timeout=0.1
            )
        except:
            pass  # Ignore timeout errors for real-time streaming
    
    def send_video(self, image_data):
        """Send video frame to Flask backend"""
        try:
            image_base64 = base64.b64encode(image_data).decode()
            requests.post(
                f"{self.flask_url}/video", 
                json={"image": image_base64}, 
                timeout=0.1
            )
        except:
            pass  # Ignore timeout errors for real-time streaming
    
    def get_transcript(self):
        """Get transcript from Flask backend"""
        try:
            response = requests.get(f"{self.flask_url}/transcript", timeout=1)
            return response.json().get("transcript", [])
        except:
            return []
    
    def get_status(self):
        """Get session status from Flask backend"""
        try:
            response = requests.get(f"{self.flask_url}/status", timeout=1)
            return response.json()
        except:
            return {"running": False, "paused": False}
    
    def check_connection(self):
        """Check if Flask server is running"""
        try:
            response = requests.get(f"{self.flask_url}/status", timeout=2)
            return response.status_code == 200
        except:
            return False
