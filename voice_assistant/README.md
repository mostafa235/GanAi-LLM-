# 🎤 Voice Assistant

A web-based voice assistant application that allows users to interact via text or speech. The assistant transcribes audio, processes requests through an AI model, and responds with both text and synthesized speech.

---

## 🎥 Demo Video

[Insert demo video here - Show recording audio, transcription, AI response, and TTS playback]

Example flow:
1. User speaks "السلام عليكم"
2. Whisper transcribes to Arabic text
3. AI generates intelligent response
4. Response plays automatically as speech

---

## ✨ Features

- **Text Chat** (`/chat`): Send text messages and get AI responses
- **Voice Recording** (`/transcribe`): Record audio (5 seconds), transcribe with Whisper, and get intelligent responses
- **Text-to-Speech** (`/synthesize`): Automatic voice synthesis for all responses
- **Conversation Memory**: Maintains conversation history for contextual responses
- **Multi-language Support**: Arabic/English support (configurable)

---

## 📋 Requirements

- Python 3.8+
- Microphone (for audio recording)
- HuggingFace API Token
- Modern web browser with Web Audio API support

---

## 🚀 Installation

### 1. Clone/Setup Project
```bash
cd voice_assistant
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the project root:
```
HUGGINGFACEHUB_API_TOKEN="your_hf_token_here"
```

Get your token from: https://huggingface.co/settings/tokens

### 4. Run the Application
```bash
python app.py
```

The app will start at: `http://localhost:5000`

---

## 📖 Usage

### **Text Input**
1. Type your message in the text field
2. Click "أرسل نص" (Send Text)
3. Wait for the AI response
4. Audio will play automatically

### **Voice Recording**
1. Click "🎤 أرسل تسجيل" (Send Recording)
2. Grant microphone permission
3. Speak for up to 5 seconds
4. The app will:
   - Transcribe your speech to text
   - Get an AI response
   - Speak the reply

---

## 🔌 API Endpoints

### `POST /chat`
Sends text to the AI and gets a response.

**Request:**
```
POST /chat
Content-Type: form-data
Body: text=<your message>
```

**Response:**
```json
{"reply": "Assistant's response text"}
```

---

### `POST /transcribe`
Records audio, transcribes it, gets AI response.

**Request:**
```
POST /transcribe
Content-Type: multipart/form-data
Body: audio=<audio file>
```

**Response:**
```json
{"reply": "Assistant's response to transcribed text"}
```

---

### `POST /synthesize`
Converts text to speech.

**Request:**
```
POST /synthesize
Content-Type: form-data
Body: text=<text to convert>
```

**Response:**
- Audio file (audio/mpeg)

---

## 🛠️ Configuration

### Language Settings
Edit `app.py` line 78 to change transcription language:
```python
language='en'  # Change to 'ar' for Arabic, etc.
```

Edit `app.py` line 122 to change TTS language:
```python
tts = gTTS(text=text, lang='en')  # Change 'en' to desired language
```

### Recording Duration
Edit `script.js` line 47 to change recording length:
```javascript
const duration = 5; // Change to desired seconds
```

### AI Model
Edit `app.py` line 51 to use a different model:
```python
model="EssentialAI/rnj-1-instruct"  # Change model ID
```

---

## 🏗️ Architecture

```
voice_assistant/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── templates/
│   └── index.html        # Web interface
└── static/
    ├── script.js         # Frontend logic
    └── style.css         # Styling
```

### How It Works

1. **Frontend** (JavaScript):
   - Records audio using Web Audio API
   - Sends text/audio to backend
   - Plays TTS responses

2. **Backend** (Flask + Python):
   - **Chat** endpoint: Processes text → HuggingFace API → Response
   - **Transcribe** endpoint: Audio → Whisper model → Text → HuggingFace API → Response
   - **Synthesize** endpoint: Text → gTTS → Audio file

3. **Models**:
   - **Speech Recognition**: OpenAI Whisper (large-v3)
   - **Chat**: EssentialAI/rnj-1-instruct (via HuggingFace)
   - **Text-to-Speech**: Google TTS (gTTS)

---

## 🔧 Troubleshooting

### Microphone Access Denied
- Grant browser microphone permission
- Check browser privacy settings

### No Audio Response
- Check internet connection
- Verify HuggingFace API token is valid
- Check browser speaker volume

### Transcription Fails
- Ensure audio is clear (5-10 seconds)
- Check microphone input levels
- Try a different language setting

### Slow Response Times
- Models may take time to load first run
- GPU acceleration recommended for faster processing
- Check internet latency

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `Flask` | Web framework |
| `transformers` | Whisper model loading |
| `torch` | PyTorch (ML framework) |
| `pydub` | Audio format conversion |
| `gtts` | Text-to-speech |
| `huggingface-hub` | HuggingFace API |

---

## 📝 Notes

- All conversation history is stored in memory (lost on restart)
- Audio recordings are temporary and deleted after processing
- Ensure `.env` file is **never** committed to version control

---

## 📄 License

Open source - Free to use and modify

---

## 🤝 Support

For issues or questions, check the logs in the terminal for detailed error messages.

Happy chatting! 🎉
