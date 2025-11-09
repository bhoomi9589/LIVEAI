# 🤖 Gemini Live Assistant

A real-time multimodal assistant powered by Google's Gemini 2.0 Live API. Chat with AI using your voice and camera!

## Features

- 🎥 Real-time video streaming from your camera
- 🎤 Voice conversations with Gemini
- 💬 Live transcript display
- 🔧 Tool calling support (Google Search)
- 🌐 Runs on Streamlit Cloud

## Deployment on Streamlit Cloud

### 1. Prerequisites

- A Google AI Studio API key ([Get one here](https://aistudio.google.com/app/apikey))
- A GitHub account

### 2. Deploy to Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repository: `LIVEAI`
5. Set **Main file path**: `app.py`
6. Click "Advanced settings"
7. Add your secret:
   ```toml
   GEMINI_API_KEY = "your-api-key-here"
   ```
8. Click "Deploy"

### 3. Using the App

1. Open your deployed app
2. Allow camera and microphone permissions when prompted
3. Click the **START** button in the WebRTC player
4. Click **🚀 Start Session** to connect to Gemini
5. Start speaking! Gemini will respond with audio and text

## Local Development

### Setup

```bash
# Clone the repository
git clone https://github.com/bhoomi9589/LIVEAI.git
cd LIVEAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

### Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## How It Works

### Architecture

```
Browser (WebRTC) ──> Streamlit UI ──> Gemini Live API
     ↑                    ↓              ↓
  Camera/Mic         Session Mgmt    AI Processing
     ↑                    ↓              ↓
     └────────────── Audio Response ─────┘
```

### Key Components

- **`app.py`**: Main Streamlit application with session management
- **`live.py`**: Gemini Live API client with async receive loop
- **`ui.py`**: WebRTC UI components and layout
- **`requirements.txt`**: Python dependencies
- **`packages.txt`**: System dependencies for Streamlit Cloud

### Technology Stack

- **Streamlit**: Web framework
- **streamlit-webrtc**: Browser WebRTC integration
- **google-genai**: Official Gemini API client
- **PyAV**: Audio/video frame processing

## Troubleshooting

### Camera/Microphone Not Working

- Ensure you granted browser permissions
- Try using HTTPS (required for WebRTC)
- Check if another app is using the camera

### API Errors

- Verify your API key is correct
- Check you have Gemini 2.0 API access
- Ensure the API key is set in Streamlit secrets (for cloud) or `.env` (for local)

### Session Not Starting

- Check the browser console for errors
- Refresh the page and try again
- Ensure you're using a supported browser (Chrome, Edge, Firefox)

## Limitations

- WebRTC requires HTTPS (automatically provided by Streamlit Cloud)
- Audio playback from Gemini is handled client-side
- Maximum conversation length depends on API quotas

## License

MIT License - feel free to use and modify!

## Credits

Built with:
- [Google Gemini API](https://ai.google.dev/)
- [Streamlit](https://streamlit.io/)
- [streamlit-webrtc](https://github.com/whitphx/streamlit-webrtc)
