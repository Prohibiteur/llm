import urllib.request
import urllib.parse
import json
import threading
import time
import os
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import queue
import random

app = FastAPI()

# Global state
words = []
tokens = []
current_token_index = 0
channel_id = ""
user_id = ""
prefix = "**"
num_pings = 10
delay = 0.2  # Safe but aggressive
spam_running = False
log_queue = queue.Queue()
ping_string = "<@{user_id}> "
sent_count = 0

# HTML/CSS for ultra-classy interface
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
            width: 700px;
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
        .or { text-align: center; color: #888; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo"></div>
        <h1>Cardio Spammer Ultra</h1>
        <form method="post" action="/start" enctype="multipart/form-data">
            <label>ID Salon</label>
            <input type="text" name="channel_id" placeholder="123456789012345678" required>
            <label>ID à Ping</label>
            <input type="text" name="user_id" placeholder="123456789012345678" required>
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
            <textarea name="token_input" rows="3" placeholder="token1\ntoken2" required></textarea>
            <label>Délai (secondes)</label>
            <input type="number" name="delay" value="0.2" min="0.1" step="0.1">
            <button type="submit">DÉMARRER</button>
        </form>
        <form method="post" action="/stop">
            <button type="submit" class="stop">ARRÊTER</button>
        </form>
        <div class="log-box" id="logs"></div>
    </div>
    <script>
        const logBox = document.getElementById('logs');
        const source = new EventSource('/logs');
        source.onmessage = function(event) {
            const log = document.createElement('div');
            log.textContent = `[${new Date().toTimeString().slice(0,8)}] ${event.data}`;
            logBox.appendChild(log);
            logBox.scrollTop = logBox.scrollHeight;
        };
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

def send_message(token: str, channel_id: str, content: str, prefix: str, num_pings: int, user_id: str):
    global sent_count
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    formatted = f"{prefix}{content}{prefix}" if prefix and prefix != "#" else f"{prefix}{content}"
    msg = f"<@{user_id}> " * num_pings + formatted
    payload = json.dumps({"content": msg}).encode("utf-8")
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            sent_count += 1
            log_queue.put(f"Sent: {msg} ({sent_count} total)")
            return True, 0
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
            err = json.loads(body) if body else {}
            if e.code == 429:
                retry_after = float(err.get("retry_after", 1000)) / 1000
                log_queue.put(f"Rate limit: Waiting {retry_after}s")
                return False, retry_after
            elif e.code == 401:
                log_queue.put("Token invalid")
                return False, "invalid"
            else:
                log_queue.put(f"Error: {e.code} - {body[:50]}...")
                return False, 0
        except:
            log_queue.put("Request error: Parse failed")
            return False, 0
    except Exception as e:
        log_queue.put(f"Request failed: {str(e)}")
        return False, 0

def spam_worker():
    global spam_running, current_token_index, sent_count
    idx = 0
    while spam_running and tokens:
        token = tokens[current_token_index]
        word = words[idx % len(words)]
        success, retry = send_message(token, channel_id, word, prefix, num_pings, user_id)
        if success:
            idx += 1
            time.sleep(random.uniform(delay, delay + 0.005))
        else:
            if retry == "invalid":
                current_token_index = (current_token_index + 1) % len(tokens)
                log_queue.put(f"Switched to token {current_token_index + 1}")
            elif isinstance(retry, (int, float)):
                if retry > 5:
                    current_token_index = (current_token_index + 1) % len(tokens)
                    log_queue.put(f"Rate limit too long, switched to token {current_token_index + 1}")
                else:
                    time.sleep(retry + 0.1)
            else:
                time.sleep(0.5)
    spam_running = False
    log_queue.put(f"Spam stopped. Total sent: {sent_count}")

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_TEMPLATE

@app.post("/start")
async def start_spam(
    channel_id: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(None),
    text: str = Form(None),
    num_pings: int = Form(10),
    prefix: str = Form("**"),
    token_input: str = Form(...),
    delay: float = Form(0.2)
):
    global words, tokens, current_token_index, channel_id, user_id, prefix, num_pings, delay, spam_running, sent_count, ping_string
    if spam_running:
        raise HTTPException(status_code=400, detail="Spam already running")
    
    # Validate tokens
    token_list = [t.strip() for t in token_input.split("\n") if t.strip()]
    valid_tokens = []
    for token in token_list:
        if validate_token(token):
            valid_tokens.append(token)
            log_queue.put(f"Token valid")
        else:
            log_queue.put(f"Token invalid: {token[:10]}...")
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
    
    # Set globals
    tokens = valid_tokens
    current_token_index = 0
    channel_id = channel_id.strip()
    user_id = user_id.strip()
    ping_string = f"<@{user_id}> "
    prefix = prefix.strip()
    num_pings = max(0, num_pings)
    delay = max(0.1, delay)
    sent_count = 0
    spam_running = True
    
    # Start spam
    threading.Thread(target=spam_worker, daemon=True).start()
    log_queue.put(f"Spam started with {len(words)} words, {len(tokens)} token(s)")
    return {"message": "Spam started", "status": "Running"}

@app.post("/stop")
async def stop_spam():
    global spam_running
    spam_running = False
    log_queue.put("Spam stopped")
    return {"message": "Spam stopped"}

@app.get("/logs")
async def logs():
    async def stream_logs():
        while True:
            try:
                log = log_queue.get_nowait()
                yield f"data: {log}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.1)
    return StreamingResponse(stream_logs(), media_type="text/event-stream")

@app.get("/status")
async def status():
    return {
        "status": "Running" if spam_running else "Stopped",
        "sent": sent_count,
        "token": tokens[current_token_index][:15] + "..." if tokens and current_token_index < len(tokens) else "N/A"
    }

if __name__ == "__main__":
    import uvicorn
    print("""
 ╔══════════════════════════════════════════════════╗
 ║         CARDIO SPAMMER ULTRA - iSH OPTIMIZED     ║
 ║     FastAPI • urllib.request • 100% Native       ║
 ║           localhost:8080 • Ultra Classy UI       ║
 ╚══════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="127.0.0.1", port=8080)
