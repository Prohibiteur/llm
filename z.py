# -*- coding: utf-8 -*-
"""
CARDIO SPAMMER v13.0 - iSH STABLE & ROBUST
100% natif Python • http.server + urllib.request
Interface épurée • Upload .txt • Token fiable
FIX : BrokenPipeError + Token invalide corrigé
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import threading
import random
import time
import os

# ===================================
# CONFIG
# ===================================
PORT = 8080
SPAM_RUNNING = False
SPAM_THREAD = None
TOKENS = []
CURRENT_TOKEN = 0
CONFIG = {
    "channel_id": "",
    "user_id": "",
    "words": [],
    "pings_per_word": 10,
    "prefix": "**",
    "sent_count": 0
}

# ===================================
# HTML ÉPURÉ
# ===================================
HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cardio Spammer v13</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: 'Courier New', monospace; }
        body { background:#000; color:#fff; padding:20px; line-height:1.6; }
        .card { max-width:700px; margin:auto; background:#111; padding:30px; border:1px solid #333; border-radius:8px; }
        h1 { text-align:center; margin-bottom:25px; font-size:24px; }
        label { display:block; margin:15px 0 5px; font-weight:bold; }
        input, textarea, select, button {
            width:100%; padding:12px; margin:6px 0; background:#222; color:#fff; border:1px solid #444; border-radius:4px; font-size:16px;
        }
        button { background:#fff; color:#000; font-weight:bold; cursor:pointer; transition:0.2s; }
        button:hover { background:#ddd; }
        button.stop { background:#ff3333; color:#fff; }
        button.stop:hover { background:#cc0000; }
        .status { padding:12px; background:#222; border-left:4px solid #fff; margin:20px 0; font-weight:bold; }
        .log { height:180px; overflow-y:auto; background:#000; padding:10px; border:1px solid #444; font-size:14px; margin-top:15px; }
        .log div { margin:2px 0; white-space:pre-wrap; }
        .file-input { margin:10px 0; }
        .or { text-align:center; margin:10px 0; color:#888; }
    </style>
</head>
<body>
<div class="card">
    <h1>CARDIO SPAMMER v13</h1>
    <div class="status" id="status">Status: En attente</div>

    <label>ID Salon</label>
    <input type="text" id="channel" placeholder="123456789012345678">

    <label>ID à Ping</label>
    <input type="text" id="user" placeholder="123456789012345678">

    <label>Fichier .txt (ou texte ci-dessous)</label>
    <input type="file" id="file" accept=".txt" class="file-input">

    <div class="or">— OU —</div>

    <label>Texte (un mot par ligne)</label>
    <textarea id="text" rows="5" placeholder="Je\nSuis\nTon\nPere"></textarea>

    <label>Pings par message</label>
    <input type="number" id="pings" value="10" min="1">

    <label>Style</label>
    <select id="style">
        <option value="**">Gras (**)</option>
        <option value="||">Spoiler (||)</option>
        <option value="__">Souligné (__)</option>
        <option value="~~">Barré (~~)</option>
        <option value="">Aucun</option>
    </select>

    <label>Tokens (un par ligne)</label>
    <textarea id="tokens" rows="3" placeholder="token1\ntoken2"></textarea>

    <button onclick="start()">DÉMARRER</button>
    <button onclick="stop()" class="stop">ARRÊTER</button>

    <div class="log" id="log"></div>
</div>

<script>
function log(msg) {
    const log = document.getElementById('log');
    const time = new Date().toTimeString().slice(0,8);
    log.innerHTML += `<div>[${time}] ${msg}</div>`;
    log.scrollTop = log.scrollHeight;
}

async function start() {
    const file = document.getElementById('file').files[0];
    let words = [];
    if (file) {
        words = (await file.text()).trim().split('\\n').filter(w => w.trim());
    } else {
        words = document.getElementById('text').value.trim().split('\\n').filter(w => w.trim());
    }

    const data = {
        channel_id: document.getElementById('channel').value.trim(),
        user_id: document.getElementById('user').value.trim(),
        words: words,
        pings_per_word: parseInt(document.getElementById('pings').value) || 10,
        prefix: document.getElementById('style').value,
        tokens: document.getElementById('tokens').value.trim().split('\\n').filter(t => t.trim())
    };

    if (!data.channel_id || !data.user_id || !data.words.length || !data.tokens.length) {
        alert("Tous les champs obligatoires !");
        return;
    }

    document.getElementById('status').innerText = "Status: Vérification tokens...";
    log("Vérification des tokens...");

    try {
        const res = await fetch('/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const json = await res.json();
        log(json.message);
        document.getElementById('status').innerText = json.status;
    } catch(e) {
        log("Erreur réseau: " + e.message);
    }
}

async function stop() {
    try {
        await fetch('/stop', {method: 'POST'});
        document.getElementById('status').innerText = "Status: Arrêté";
        log("Arrêt demandé.");
    } catch(e) {}
}

setInterval(async () => {
    try {
        const res = await fetch('/status');
        const d = await res.json();
        document.getElementById('status').innerText = `Status: ${d.status} | Envoyés: ${d.sent} | Token: ${d.token}`;
    } catch(e) {}
}, 1000);
</script>
</body>
</html>"""

# ===================================
# API DISCORD (urllib.request) - ROBUSTE
# ===================================
def send_message(token, channel_id, content):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    payload = json.dumps({"content": content}).encode()
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
            err = json.loads(body) if body else {}
            if e.code == 429:
                retry = float(err.get("retry_after", 1))
                return False, retry
            elif e.code == 401:
                return False, "invalid"
            else:
                return False, f"error {e.code}"
        except:
            return False, "parse error"
    except Exception as e:
        return False, "timeout"

def validate_token(token):
    """Vérification 100% fiable du token"""
    token = token.strip()
    if not token or len(token) < 50:
        return False
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v9/users/@me",
            headers={
                "Authorization": token,
                "User-Agent": "Mozilla/5.0"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            return bool(data.get("id"))
    except:
        return False

# ===================================
# SPAM WORKER - STABLE
# ===================================
def spam_worker():
    global SPAM_RUNNING, CURRENT_TOKEN, CONFIG
    idx = 0
    while SPAM_RUNNING and CURRENT_TOKEN < len(TOKENS):
        token = TOKENS[CURRENT_TOKEN]
        word = CONFIG["words"][idx % len(CONFIG["words"])]
        formatted = f"{CONFIG['prefix']}{word}{CONFIG['prefix']}" if CONFIG['prefix'] else word
        ping = f"<@{CONFIG['user_id']}>"
        msg = f"{ping} " * CONFIG["pings_per_word"] + formatted

        success, info = send_message(token, CONFIG["channel_id"], msg)
        if success:
            CONFIG["sent_count"] += 1
            idx += 1
            time.sleep(random.uniform(0.011, 0.016))
        else:
            if info == "invalid":
                print(f"Token invalide → skip")
                CURRENT_TOKEN += 1
            elif isinstance(info, (int, float)):
                print(f"Rate limit {info}s → switch token")
                time.sleep(info + 0.1)
                CURRENT_TOKEN += 1
            else:
                time.sleep(0.5)

    SPAM_RUNNING = False
    print(f"Spam terminé. {CONFIG['sent_count']} messages envoyés.")

# ===================================
# HTTP HANDLER - FIX BROKEN PIPE
# ===================================
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == "/":
                self._send_html()
            elif self.path == "/status":
                self._send_json({
                    "status": "En cours" if SPAM_RUNNING else "Arrêté",
                    "sent": CONFIG["sent_count"],
                    "token": TOKENS[CURRENT_TOKEN-1][:15]+"..." if TOKENS and CURRENT_TOKEN > 0 else "N/A"
                })
        except BrokenPipeError:
            pass
        except Exception as e:
            print(f"GET error: {e}")

    def do_POST(self):
        try:
            if self.path == "/start":
                length = int(self.headers.get("Content-Length", 0))
                if length <= 0:
                    self._send_json({"message": "Aucune donnée", "status": "Erreur"}, 400)
                    return
                raw = self.rfile.read(length).decode("utf-8", errors="ignore")
                data = json.loads(raw)

                valid = [t for t in data["tokens"] if validate_token(t)]
                if not valid:
                    self._send_json({"message": "Aucun token valide", "status": "Échec"}, 400)
                    return

                global TOKENS, CURRENT_TOKEN, CONFIG, SPAM_RUNNING, SPAM_THREAD
                TOKENS = valid
                CURRENT_TOKEN = 0
                CONFIG.update({
                    "channel_id": data["channel_id"],
                    "user_id": data["user_id"],
                    "words": data["words"],
                    "pings_per_word": data["pings_per_word"],
                    "prefix": data["prefix"],
                    "sent_count": 0
                })

                if SPAM_RUNNING:
                    SPAM_RUNNING = False
                    if SPAM_THREAD: SPAM_THREAD.join(timeout=1)

                SPAM_RUNNING = True
                SPAM_THREAD = threading.Thread(target=spam_worker, daemon=True)
                SPAM_THREAD.start()

                self._send_json({
                    "message": f"{len(TOKENS)} token(s) valide(s) → démarré",
                    "status": "En cours"
                })

            elif self.path == "/stop":
                global SPAM_RUNNING
                SPAM_RUNNING = False
                self._send_json({"message": "Arrêté"})

        except BrokenPipeError:
            pass
        except Exception as e:
            print(f"POST error: {e}")
            self._send_json({"message": "Erreur serveur", "status": "Erreur"}, 500)

    def _send_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        try:
            self.wfile.write(HTML.encode("utf-8"))
        except BrokenPipeError:
            pass

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(json.dumps(data).encode("utf-8"))
        except BrokenPipeError:
            pass

    def log_message(self, *args): pass  # Silence logs

# ===================================
# MAIN
# ===================================
def main():
    print("""
 ╔══════════════════════════════════════════════════╗
 ║            CARDIO SPAMMER v13 - iSH STABLE       ║
 ║        FIX BrokenPipe + Token 100% fiable        ║
 ║           100% natif • localhost:8080            ║
 ╚══════════════════════════════════════════════════╝
    """)
    print(f" → http://localhost:{PORT}\n")

    server = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt propre.")

if __name__ == "__main__":
    mainzlich
