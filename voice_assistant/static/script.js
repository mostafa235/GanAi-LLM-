document.addEventListener("DOMContentLoaded", () => {
    console.log("JS READY ✅");

    const replyP = document.getElementById("reply");
    const textInput = document.getElementById("textInput");
    const sendTextBtn = document.getElementById("sendTextBtn");
    const sendAudioBtn = document.getElementById("sendAudioBtn");

    if (!sendTextBtn || !sendAudioBtn) {
        console.error("Buttons not found ❌");
        return;
    }

    // إرسال النص
    sendTextBtn.addEventListener("click", async () => {
        const text = textInput.value;
        if (!text) return;

        replyP.innerText = "...";

        try {
            const formData = new FormData();
            formData.append("text", text);

            const res = await fetch("/chat", { method: "POST", body: formData });
            if (!res.ok) throw new Error(`Server error: ${res.status}`);

            const data = await res.json();
            replyP.innerText = data.reply;
            playTTS(data.reply);

        } catch (err) {
            console.error("Error:", err);
            replyP.innerText = "خطأ: " + err.message;
        }
    });

    // تسجيل الصوت وإرساله
    sendAudioBtn.addEventListener("click", async () => {
        sendAudioBtn.disabled = true;
        replyP.innerText = "🎙️ جاري التسجيل والمعالجة...";

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            const chunks = [];

            mediaRecorder.ondataavailable = e => chunks.push(e.data);
            mediaRecorder.start();

            const duration = 5; // مدة التسجيل بالثواني
            await new Promise(resolve => setTimeout(resolve, duration * 1000));
            mediaRecorder.stop();
            await new Promise(resolve => mediaRecorder.addEventListener("stop", resolve));

            const audioBlob = new Blob(chunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append("audio", audioBlob, "record.webm");

            const res = await fetch("/transcribe", { method: "POST", body: formData });
            if (!res.ok) throw new Error(`Server error: ${res.status}`);

            const data = await res.json();
            replyP.innerText = data.reply;
            playTTS(data.reply);

        } catch (err) {
            console.error("Recording error:", err);
            replyP.innerText = "خطأ: " + err.message;
        } finally {
            sendAudioBtn.disabled = false;
        }
    });

    // تحويل النص لصوت وتشغيله
    async function playTTS(text) {
        try {
            const fd = new FormData();
            fd.append("text", text);

            const res = await fetch("/synthesize", { method: "POST", body: fd });
            if (!res.ok) throw new Error("TTS failed");

            const blob = await res.blob();
            const audio = new Audio(URL.createObjectURL(blob));
            await audio.play();
        } catch (err) {
            console.error("TTS error:", err);
        }
    }
});
