from flask import Flask, render_template,request,send_file
from dotenv import load_dotenv
import os
import io
import tempfile
from gtts import gTTS
from huggingface_hub import InferenceClient
import whisper
import numpy as np
from scipy.io import wavfile
from pydub import AudioSegment

import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

from datasets import load_dataset

load_dotenv()
# Load model directly
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32



processor = AutoProcessor.from_pretrained("openai/whisper-large-v3")
model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-large-v3")
model.to(device)

app = Flask(__name__)

# Home route
@app.route('/')
def home():
    return render_template('index.html')

HUGGINGFACEHUB_API_TOKEN=os.getenv("HUGGINGFACEHUB_API_TOKEN")

HF_TOKEN=HUGGINGFACEHUB_API_TOKEN

# OpenAI client setup
client = InferenceClient(
    api_key=HF_TOKEN
)
messages = [
    {"role": "system", "content": "You are a helpful assistant."}
]
@app.route('/chat', methods=['POST'])
def chat():
    global messages
    text=request.form['text']
    messages.append({"role": "user", "content":text})

    completion = client.chat.completions.create(
        model="EssentialAI/rnj-1-instruct",
        messages=messages,
    )

    last_reply = completion.choices[-1].message['content']
    
    # حفظ الرد في history
    messages.append({"role": "assistant", "content": last_reply})
    
    return {"reply": last_reply}


# Function to transcribe audio using speech_recognition library
@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    global messages
    

    audio_file = request.files['audio']  # الصوت اللي جاي من المستخدم

    # حفظه مؤقتًا كـ WAV
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        audio_file.save(temp_audio.name)
        temp_path = temp_audio.name

    # تحويل الصوت لـ WAV 16k mono
    audio = AudioSegment.from_file(temp_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(temp_path, format="wav")

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
        language='en'
    )

#get text stt


    result = pipe(temp_path)
    print(result["text"])

    messages.append({"role": "user", "content":result["text"]})
    
    completion = client.chat.completions.create(
        model="EssentialAI/rnj-1-instruct",
        messages=messages,
    )

    last_reply = completion.choices[-1].message.get('content', 'لا توجد إجابة')
    
    # حفظ الرد في history
    messages.append({"role": "assistant", "content": last_reply})
    print(last_reply)
    
    return {"reply": last_reply}





# Function to convert text to speech using Hugging Face Inference API
@app.route('/synthesize', methods=['POST'])
def synthesize():
    text = request.form['text']  # النص المرسل من المتصفح
    
    # توليد الصوت
    tts = gTTS(text=text, lang='en')  # ممكن تغير 'en' لأي لغة مدعومة
    audio_bytes = io.BytesIO()
    tts.write_to_fp(audio_bytes)
    audio_bytes.seek(0)
    
    # إرسال الصوت للمتصفح
    return send_file(
        audio_bytes,
        mimetype='audio/mpeg',
        as_attachment=False,
        download_name='reply.mp3'
    )


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)