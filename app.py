from flask import Flask, request, jsonify, Response
import asyncio
import threading
import cv2
import mss
import numpy as np
import time
from live import AudioLoop

app = Flask(__name__)

# -----------------------
# Global state
# -----------------------
audio_loop_instance = None
loop_thread = None
status = "stopped"  # Can be: stopped, running, paused
cap = None          # Camera object
mode = "none"       # camera, screen, or none

# -----------------------
# Thread Target Function
# -----------------------
def run_audio_loop_in_thread(selected_mode):
    """This function runs in the background thread to handle the Gemini session."""
    global audio_loop_instance
    audio_loop_instance = AudioLoop(video_mode=selected_mode)
    asyncio.run(audio_loop_instance.run())
    print("AudioLoop has finished.")

# -----------------------
# API Endpoints
# -----------------------

@app.route("/")
def index():
    return "API is running"

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify({"status": status, "mode": mode})

@app.route("/start", methods=["POST"])
def start_session():
    global loop_thread, status, mode, cap
    
    if status != "stopped":
        return jsonify({"status": "error", "message": f"Session is already {status}"}), 400

    requested_mode = request.json.get("mode", "camera")
    
    if requested_mode == "camera":
        print("Initializing camera...")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("Error: Failed to open camera.")
            return jsonify({"status": "error", "message": "Failed to open camera"}), 500
        print("Camera initialized successfully.")
    
    mode = requested_mode
    loop_thread = threading.Thread(target=run_audio_loop_in_thread, args=(mode,), daemon=True)
    loop_thread.start()
    status = "running"
    
    return jsonify({"status": "success", "message": f"Session started in {mode} mode"})

@app.route("/pause", methods=["POST"])
def pause_session():
    global audio_loop_instance, loop_thread, status, cap
    
    if status != "running":
        return jsonify({"status": "error", "message": "Only a running session can be paused"}), 400

    if audio_loop_instance:
        audio_loop_instance.stop()
    
    if loop_thread and loop_thread.is_alive():
        loop_thread.join(timeout=5)
    
    # === FIX: Release the camera resource on pause ===
    if cap:
        print("Releasing camera on pause...")
        cap.release()
        cap = None
    
    status = "paused"
    return jsonify({"status": "success", "message": "Session paused"})

@app.route("/resume", methods=["POST"])
def resume_session():
    global loop_thread, status, mode, cap
    
    if status != "paused":
        return jsonify({"status": "error", "message": "No paused session to resume"}), 400

    # === FIX: Re-initialize the camera on resume ===
    if mode == "camera":
        print("Re-initializing camera on resume...")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("Error: Failed to re-open camera.")
            return jsonify({"status": "error", "message": "Failed to re-open camera on resume"}), 500

    loop_thread = threading.Thread(target=run_audio_loop_in_thread, args=(mode,), daemon=True)
    loop_thread.start()
    status = "running"
    
    return jsonify({"status": "success", "message": "Session resumed"})

@app.route("/stop", methods=["POST"])
def stop_session():
    global audio_loop_instance, loop_thread, status, cap, mode
    
    if status == "stopped":
        return jsonify({"status": "error", "message": "No session to stop"}), 400

    try:
        if audio_loop_instance:
            audio_loop_instance.stop()
        
        if loop_thread and loop_thread.is_alive():
            loop_thread.join(timeout=5)
        
        if cap:
            print("Releasing camera...")
            cap.release()
        
        # Reset all global state variables
        audio_loop_instance = None
        loop_thread = None
        cap = None
        status = "stopped"
        mode = "none"
        
        return jsonify({"status": "success", "message": "Session stopped"})
    except Exception as e:
        print(f"Error during stop: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/frame", methods=["GET"])
def get_frame():
    global cap, status, mode
    if status != "running":
        return jsonify({"status": "error", "message": f"Session is {status}, not running"}), 400

    try:
        frame = None
        if mode == "camera":
            if cap is None or not cap.isOpened():
                return jsonify({"status": "error", "message": "Camera not available"}), 500
            ret, frame = cap.read()
            if not ret:
                return jsonify({"status": "error", "message": "Failed to read frame from camera"}), 500
        elif mode == "screen":
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)

        if frame is None:
            return jsonify({"status": "error", "message": "No frame captured"}), 500

        _, jpeg = cv2.imencode(".jpg", frame)
        return Response(jpeg.tobytes(), mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Frame capture error: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=False, port=5000, host='0.0.0.0', use_reloader=False)