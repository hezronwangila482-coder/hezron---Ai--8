from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os, requests, io, base64
from datetime import datetime

app = Flask(__name__)
CORS(app)

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

def ask_ai(messages, model="gpt-4o-mini", max_tokens=2000):
    if not OPENAI_KEY:
        return "OFFLINE_MODE: I am LIVE but my OpenAI API key is missing on Render. Go to Render > Environment > Add OPENAI_API_KEY."
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3},
            timeout=90)
        j = r.json()
        if "choices" in j:
            return j["choices"][0]["message"]["content"]
        err = j.get("error", {}).get("message", str(j)[:300])
        if "quota" in err.lower():
            return "Your OpenAI balance is finished. Top up at platform.openai.com or use a new API key."
        if "invalid" in err.lower() and "key" in err.lower():
            return "Your API key is wrong. Check Render > Environment > OPENAI_API_KEY."
        return f"AI said: {err}"
    except Exception as e:
        return f"Connection problem: {str(e)}. Try again."

def get_news():
    try:
        if not NEWS_API_KEY: return ""
        r = requests.get(f"https://newsapi.org/v2/everything?q=Kenya&sortBy=publishedAt&pageSize=3&apiKey={NEWS_API_KEY}", timeout=10)
        arts = r.json().get("articles", [])
        return "\n".join([f"- {a['title']}: {a.get('description','')}" for a in arts])
    except: return ""

SYSTEM_BASE = """You are HEZRON AI 8.0, created by Hezron Wangila from Mau Narok, student at MMUST.
You know EVERYTHING. Never guess. Think step by step.
For Maths/Science: Formula -> Substitute -> Calculate -> Final Answer with units.
For MCQ: Give correct letter + why others are wrong.
For KCSE/University: Use Kenyan curriculum marking scheme.
For multi-part (a,b,c): Answer ALL parts.
Always end with: ✅ FINAL ANSWER: ...
Answer in same language as user: English, Swahili, or Sheng.
Today is {today}. Live news: {news}
"""

@app.route("/")
def home(): return "HEZRON AI 8.0 IS LIVE - FIXED"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        msg = data.get("message","").strip()
        if not msg: return jsonify({"answer": "Niulize chochote mkuu!"})
        low = msg.lower()
        today = datetime.now().strftime("%d %B %Y")
        news = get_news()
        if "create image" in low or "generate image" in low or "image of" in low or "create an image" in low:
            if not OPENAI_KEY: return jsonify({"answer": "To create images, add OPENAI_API_KEY on Render first."})
            try:
                prompt = msg.replace("Create image","").replace("create an image","").strip() or msg
                r = requests.post("https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                    json={"model": "dall-e-3", "prompt": prompt, "size": "1024x1024", "n": 1}, timeout=90)
                j = r.json()
                if "data" in j: return jsonify({"answer": f"Done! Image for: '{prompt}'", "image_url": j["data"][0]["url"]})
                return jsonify({"answer": f"Could not create image: {j.get('error',{}).get('message','Check balance')}"})
            except Exception as e: return jsonify({"answer": f"Image error: {str(e)}"})
        if "video" in low or "tiktok" in low or "reel" in low:
            sys = SYSTEM_BASE.format(today=today, news=news) + "\nYou are also a video director. Give: Hook (3 sec), 3 Scenes, Full Script, Captions, Hashtags, Music, and Text-to-Video prompt for Runway/Pika/Kling."
            ans = ask_ai([{"role":"system","content":sys},{"role":"user","content":msg}])
            return jsonify({"answer": ans})
        sys = SYSTEM_BASE.format(today=today, news=news)
        ans = ask_ai([{"role":"system","content":sys},{"role":"user","content":msg}])
        return jsonify({"answer": ans})
    except Exception as e:
        return jsonify({"answer": f"Backend error fixed: {str(e)}"})

@app.route("/scan", methods=["POST"])
def scan():
    try:
        if "image" not in request.files: return jsonify({"answer": "No image uploaded. Take a clear photo."})
        file = request.files["image"]
        instruction = request.form.get("instruction","Scan this question and solve it correctly step by step.")
        img_bytes = file.read()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        if not OPENAI_KEY: return jsonify({"answer": "Scan needs OPENAI_API_KEY on Render. Add it first."})
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o", "messages": [
                {"role":"system","content":"You are HEZRON AI 8.0, top Kenyan teacher. 1. Quote question EXACTLY. 2. Identify subject. 3. Solve STEP BY STEP, show all working. 4. For Maths: formula, substitution, calc, final answer with units. 5. For MCQ: correct letter + why others wrong. 6. Use KCSE/KNEC style. 7. End with ✅ FINAL ANSWER: ..."},
                {"role":"user","content":[{"type":"text","text":instruction},{"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}]}
            ], "max_tokens": 2500}, timeout=90)
        j = r.json()
        if "choices" not in j: return jsonify({"answer": f"Scan failed: {j.get('error',{}).get('message','Check API key')}"})
        return jsonify({"answer": j["choices"][0]["message"]["content"]})
    except Exception as e: return jsonify({"answer": f"Scan error: {str(e)}"})

@app.route("/remove-bg", methods=["POST"])
def remove_bg():
    try:
        from rembg import remove
        from PIL import Image
        file = request.files["image"]
        img = Image.open(file.stream)
        out = remove(img)
        buf = io.BytesIO(); out.save(buf, format="PNG"); buf.seek(0)
        return send_file(buf, mimetype="image/png")
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
