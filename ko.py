import urllib.request
import urllib.parse
import json
import threading
import time
import os
import random
import string
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import queue

app = FastAPI()

# Gestion d'état
class State:
    def __init__(self):
        self.words = []
        self.tokens = []
        self.current_token_index = 0
        self.channel_id = ""
        self.user_ids = []
        self.prefix = "**"
        self.num_pings = 10
        self.delay = 0.2
        self.spam_running = False
        self.sent_count = 0
        self.log_queue = queue.Queue()
        self.start_time = 0

state = State()

# HTML/CSS ultra classe
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cardio Spammer Ultra</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a23;
            color: #e0e0e0;
            font-family: 'Orbitron', sans-serif;
            padding: 20px;
            display: flex;
            justify-content: center;
        }
        .container {
            background: #16213e;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
            width: 750px;
            text-align: center;
        }
        h1 {
            color: #0ef;
            text-shadow: 0 0 10px #0ef;
            margin-bottom: 20px;
        }
        .logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px;
            position: relative;
        }
        .logo::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, #5865f2, #7289da);
            clip-path: path('M50 10C50 4.47715 45.5228 0 40 0H20C14.4772 0 10 4.47715 10 10V30C10 35.5228 14.4772 40 20 40H25L22 50H38L35 40H40C45.5228 40 50 35.5228 50 30V10Z');
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        label {
            display: block;
            margin: 15px 0 5px;
            font-weight: bold;
            color: #0ef;
        }
        input, textarea, select, button {
            background: #0a0a23;
            color: #e0e0e0;
            border: 2px solid #0ef;
            border-radius: 5px;
            padding: 12px;
            margin: 8px 0;
            width: 100%;
            font-family: 'Orbitron', sans-serif;
            font-size: 16px;
        }
        textarea { resize: vertical; }
        button {
            background: #0ef;
            color: #1a1a2e;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        button:hover {
            background: #00b7b7;
            box-shadow: 0 0 10px #0ef;
        }
        button.stop { background: #ff3333; }
        button.stop:hover { background: #cc0000; }
        .log-box {
            background: #0a0a23;
            border: 2px solid #0ef;
            border-radius: 5px;
            height: 200px;
            overflow-y: auto;
            padding: 10px;
            margin-top: 20px;
            font-size: 14px;
            text-align: left;
        }
        .preview {
            background: #0a0a23;
            border: 2px solid #0ef;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .or { text-align: center; color: #888; margin: 10px 0; }
        .status { padding: 10px; background: #0a0a23; border-left: 4px solid #0ef; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo"></div>
        <h1>Cardio Spammer Ultra</h1>
        <div class="status" id="status">Status: En attente | Envoyés: 0 | Temps: 0s</div>
        <form method="post" action="/start" enctype="multipart/form-data">
            <label>ID Salon</label>
            <input type="text" name="channel_id" placeholder="123456789012345678" required>
            <label>IDs à Ping (un par ligne)</label>
            <textarea name="user_ids" rows="3" placeholder="123456789012345678\n987654321098765432" required></textarea>
            <label>Fichier .txt</label>
            <input type="file" name="file" accept=".txt">
            <div class="or">— OU —</div>
            <label>Texte (un mot par ligne)</label>
            <textarea name="text" rows="5" placeholder="Je\nSuis\nTon\nPere"></textarea>
            <label>Pings par message</label>
            <input type="number" name="num_pings" value="10" min="0">
            <label>Style</label>
            <select name="prefix">
                <option value="**">Gras (**)</option>
                <option value="||">Spoiler (||)</option>
                <option value="__">Souligné (__)</option>
                <option value="~~">Barré (~~)</option>
                <option value="">Aucun</option>
            </select>
            <label>Tokens (un par ligne)</label>
            <textarea name="tokens" rows="3" placeholder="token1\ntoken2" required></textarea>
            <label>Délai moyen (secondes)</label>
            <input type="number" name="delay" value="0.2" min="0.1" step="0.1">
            <label>Burst Mode (messages par salve)</label>
            <input type="number" name="burst_size" value="3" min="1" max="5">
            <label>Randomisation</label>
            <select name="randomize">
                <option value="none">Aucune</option>
                <option value="case">Maj/Min</option>
                <option value="chars">Caractères</option>
            </select>
            <button type="submit">DÉMARRER</button>
        </form>
        <form method="post" action="/stop">
            <button type="submit" class="stop">ARRÊTER</button>
        </form>
        <div class="preview" id="preview">Aperçu : (sera généré après soumission)</div>
        <div class="log-box" id="logs"></div>
    </div>
    <script>
        const logBox = document.getElementById('logs');
        const statusBox = document.getElementById('status');
        const source = new EventSource('/logs');
        source.onmessage = function(event) {
            const log = document.createElement('div');
            log.textContent = `[${new Date().toTimeString().slice(0,8)}] ${event.data}`;
            logBox.appendChild(log);
            logBox.scrollTop = logBox.scrollHeight;
        };
        setInterval(async () => {
            try {
                const res = await fetch('/status');
                const d = await res.json();
                statusBox.textContent = `Status: ${d.status} | Envoyés: ${d.sent} | Temps: ${d.time}s | Token: ${d.token}`;
            } catch(e) {}
        }, 1000);
    </script>
</body>
</html>
"""

def validate_token(token: str) -> bool:
    token = token.strip()
    if not token or len(token) < 50:
        return False
    url = "https://discord.com/api/v9/users/@me"
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "*/*",
        "Connection": "keep-alive"
    }
    req = urllib.request.Request(url, headers=headers, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except:
        return False

def randomize_content(content: str, mode: str) -> str:
    if mode == "none":
        return content
    elif mode == "case":
        return ''.join(c.upper() if random.random() > 0.5 else c.lower() for c in content)
    elif mode == "chars":
        extras = random.choices(string.ascii_letters + "._-!", k=random.randint(0, 2))
        return content + ''.join(extras)
    return content

def send_message(token: str, channel_id: str, content: str, prefix: str, num_pings: int, user_ids: list, randomize: str):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    content = randomize_content(content, randomize)
    formatted = f"{prefix}{content}{prefix}" if prefix and prefix != "#" else f"{prefix}{content}"
    pings = "".join(f"<@{uid}> " for uid in user_ids) * num_pings
    msg = pings + formatted
    payload = json.dumps({"content": msg}).encode("utf-8")
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            state.sent_count += 1
            state.log_queue.put(f"Sent: {msg} ({state.sent_count} total)")
            return True, 0
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
            err = json.loads(body) if body else {}
            if e.code == 429:
                retry_after = float(err.get("retry_after", 1000)) / 1000
                state.log_queue.put(f"Rate limit: Waiting {retry_after}s")
                return False, retry_after
            elif e.code == 401:
                state.log_queue.put("Token invalid")
                return False, "invalid"
            else:
                state.log_queue.put(f"Error: {e.code} - {body[:50]}...")
                return False, 0
        except:
            state.log_queue.put("Request error: Parse failed")
            return False, 0
    except Exception as e:
        state.log_queue.put(f"Request failed: {str(e)}")
        return False, 0

def spam_worker(burst_size: int, randomize: str):
    idx = 0
    while state.spam_running and state.tokens:
        token = state.tokens[state.current_token_index]
        for _ in range(burst_size if state.spam_running else 1):
            if not state.spam_running or not state.words:
                break
            word = state.words[idx % len(state.words)]
            success, retry = send_message(token, state.channel_id, word, state.prefix, state.num_pings, state.user_ids, randomize)
            if success:
                idx += 1
                time.sleep(random.uniform(state.delay - 0.05, state.delay + 0.05))
            else:
                if retry == "invalid":
                    state.current_token_index = (state.current_token_index + 1) % len(state.tokens)
                    state.log_queue.put(f"Switched to token {state.current_token_index + 1}")
                elif isinstance(retry, (int, float)):
                    if retry > 5:
                        state.current_token_index = (state.current_token_index + 1) % len(state.tokens)
                        state.log_queue.put(f"Rate limit too long, switched to token {state.current_token_index + 1}")
                    else:
                        time.sleep(retry + 0.1)
                else:
                    time.sleep(0.5)
                break
        if success and state.spam_running:
            time.sleep(state.delay * 2)  # Pause between bursts
    state.spam_running = False
    state.log_queue.put(f"Spam stopped. Total sent: {state.sent_count}")

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_TEMPLATE

@app.post("/start")
async def start_spam(
    channel_id_form: str = Form(...),
    user_ids_form: str = Form(...),
    file: UploadFile = File(None),
    text: str = Form(None),
    num_pings_form: int = Form(10),
    prefix_form: str = Form("**"),
    tokens_form: str = Form(...),
    delay_form: float = Form(0.2),
    burst_size_form: int = Form(3),
    randomize_form: str = Form("none")
):
    if state.spam_running:
        raise HTTPException(status_code=400, detail="Spam already running")
    
    # Validate tokens
    token_list = [t.strip() for t in tokens_form.split("\n") if t.strip()]
    valid_tokens = []
    for token in token_list:
        if validate_token(token):
            valid_tokens.append(token)
            state.log_queue.put(f"Token valid")
        else:
            state.log_queue.put(f"Token invalid: {token[:10]}...")
    if not valid_tokens:
        raise HTTPException(status_code=400, detail="No valid tokens")
    
    # Load words
    if file and file.filename:
        file_content = await file.read()
        with open("temp.txt", "wb") as f:
            f.write(file_content)
        words = [line.strip() for line in file_content.decode("utf-8").splitlines() if line.strip()]
    elif text:
        words = [line.strip() for line in text.split("\n") if line.strip()]
    else:
        raise HTTPException(status_code=400, detail="No file or text provided")
    if not words:
        raise HTTPException(status_code=400, detail="Empty input")
    
    # Set state
    state.tokens = valid_tokens
    state.current_token_index = 0
    state.channel_id = channel_id_form.strip()
    state.user_ids = [uid.strip() for uid in user_ids_form.split("\n") if uid.strip()]
    state.prefix = prefix_form.strip()
    state.num_pings = max(0, num_pings_form)
    state.delay = max(0.1, delay_form)
    state.spam_running = True
    state.sent_count = 0
    state.start_time = time.time()
    
    # Generate preview
    sample_word = words[0] if words else "test"
    sample_pings = "".join(f"<@{uid}> " for uid in state.user_ids) * state.num_pings
    sample_msg = sample_pings + (f"{state.prefix}{randomize_content(sample_word, randomize_form)}{state.prefix}" if state.prefix and state.prefix != "#" else f"{state.prefix}{randomize_content(sample_word, randomize_form)}")
    state.log_queue.put(f"Preview: {sample_msg}")
    
    # Start spam
    threading.Thread(target=spam_worker, args=(max(1, min(5, burst_size_form)), randomize_form), daemon=True).start()
    state.log_queue.put(f"Spam started with {len(words)} words, {len(valid_tokens)} token(s), burst size {burst_size_form}")
    return {"message": "Spam started", "status": "Running"}

@app.post("/stop")
async def stop_spam():
    state.spam_running = False
    state.log_queue.put("Spam stopped")
    return {"message": "Spam stopped"}

@app.get("/logs")
async def logs():
    async def stream_logs():
        while True:
            try:
                log = state.log_queue.get_nowait()
                yield f"data: {log}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.1)
    return StreamingResponse(stream_logs(), media_type="text/event-stream")

@app.get("/status")
async def status():
    elapsed = int(time.time() - state.start_time) if state.start_time else 0
    return {
        "status": "Running" if state.spam_running else "Stopped",
        "sent": state.sent_count,
        "time": elapsed,
        "token": state.tokens[state.current_token_index][:15] + "..." if state.tokens and state.current_token_index < len(state.tokens) else "N/A"
    }

if __name__ == "__main__":
    import uvicorn
    print("""
 ╔══════════════════════════════════════════════════╗
 ║     CARDIO SPAMMER ULTRA - iSH HYPER OPTIMIZED   ║
 ║     FastAPI • urllib.request • Zero Errors        ║
 ║         localhost:8080 • Futuristic UI           ║
 ╚══════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="127.0.0.1", port=8080)