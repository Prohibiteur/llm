# -*- coding: utf-8 -*-
"""
CARDIO SPAMMER v10.0 - iSH ULTRA-LIGHT
SANS discord.py, SANS aiohttp
Interface HTML locale (http.server) - 100% natif Python
API Discord HTTP pure (urllib)
Ping ID personnalisé + préfixe Markdown (**gras**, __souligné__, etc.)
Spam séquentiel ultra-rapide + rotation tokens
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
import html
from colorama import init, Fore, Style

init(autoreset=True)

# ===================================
# CONFIGURATION GLOBALE
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
    "prefix": "",
    "sent_count": 0
}

# ===================================
# PAGE HTML (servie localement)
# ===================================
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Cardio Spammer v10.0 - iSH</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: 'Courier New', monospace; background:#000; color:#0f0; padding:20px; }
        .container { max-width:900px; margin:auto; background:#111; padding:25px; border:2px solid #0f0; border-radius:12px; }
        h1 { text-align:center; margin-bottom:20px; color:#0f0; text-shadow:0 0 5px #0f0; }
        label { display:block; margin:15px 0 5px; font-weight:bold; }
        input, textarea, select, button {
            width:100%; padding:12px; margin:8px 0; background:#222; color:#0f0; border:1px solid #0f0; border-radius:6px; font-family:inherit; font-size:16px;
        }
        button { background:#0f0; color:#000; font-weight:bold; cursor:pointer; transition:0.3s; }
        button:hover { background:#0c0; }
        button.stop { background:#f00; }
        button.stop:hover { background:#c00; }
        .status { padding:15px; background:#222; border-left:5px solid #0f0; margin:20px 0; font-size:18px; }
        .log { height:220px; overflow-y:auto; background:#000; padding:12px; border:1px solid #0f0; font-size:14px; margin-top:15px; }
        .log div { margin:2px 0; }
        select { background:#222; color:#0f0; }
    </style>
</head>
<body>
<div class="container">
    <h1>CARDIO SPAMMER v10.0 - iSH</h1>
    <div class="status" id="status">Status: En attente...</div>

    <label>ID du Salon Discord</label>
    <input type="text" id="channel_id" placeholder="123456789012345678">

    <label>ID de la personne à ping</label>
    <input type="text" id="user_id" placeholder="123456789012345678">

    <label>Tokens (un par ligne)</label>
    <textarea id="tokens" rows="4" placeholder="token1&#10;token2&#10;token3"></textarea>

    <label>Mots à spam (un par ligne)</label>
    <textarea id="words" rows="6" placeholder="Je&#10;Suis&#10;Ton&#10;Pere"></textarea>

    <label>Pings par message</label>
    <input type="number" id="pings_per_word" value="10" min="1">

    <label>Style du texte (Markdown)</label>
    <select id="prefix">
        <option value="">Aucun</option>
        <option value="**" selected>**Gras**</option>
        <option value="||">||Spoiler||</option>
        <option value="__">__Souligné__</option>
        <option value="~~">~~Barré~~</option>
        <option value="`">`Code`</option>
        <option value="> ">Citation</option>
    </select>

    <button onclick="start()">DÉMARRER LE SPAM</button>
    <button onclick="stop()" class="stop">ARRÊTER</button>

    <div class="log" id="log"></div>
</div>

<script>
function log(msg) {
    const log = document.getElementById('log');
    const time = new Date().toLocaleTimeString();
    log.innerHTML += `<div>[${time}] ${msg}</div>`;
    log.scrollTop = log.scrollHeight;
}

async function start() {
    const data = {
        channel_id: document.getElementById('channel_id').value.trim(),
        user_id: document.getElementById('user_id').value.trim(),
        tokens: document.getElementById('tokens').value.trim().split('\\n').filter(t => t.trim()),
        words: document.getElementById('words').value.trim().split('\\n').filter(w => w.trim()),
        pings_per_word: parseInt(document.getElementById('pings_per_word').value) || 10,
        prefix: document.getElementById('prefix').value
    };

    if (!data.channel_id || !data.user_id || data.tokens.length === 0 || data.words.length === 0) {
        alert("Tous les champs sont obligatoires !");
        return;
    }

    document.getElementById('status').innerText = "Status: Vérification des tokens...";
    log("Vérification rapide des tokens...");

    const res = await fetch('/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const result = await res.json();
    log(result.message);
    document.getElementById('status').innerText = result.status;
}

async function stop() {
    await fetch('/stop', {method: 'POST'});
    document.getElementById('status').innerText = "Status: Arrêté";
    log("Arrêt demandé.");
}

setInterval(async () => {
    try {
        const res = await fetch('/status');
        const data = await res.json();
        document.getElementById('status').innerText = `Status: ${data.status} | Envoyés: ${data.sent} | Token: ${data.token}`;
    } catch(e) {}
}, 1000);
</script>
</body>
</html>
"""

# ===================================
# FONCTIONS API DISCORD (urllib)
# ===================================
def send_discord_message(token, channel_id, content):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    data = json.dumps({"content": content}).encode()
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return True, "OK"
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
            if e.code == 429:
                return False, f"Rate limit: {err.get('retry_after', 1)}s"
            elif e.code in (401, 403):
                return False, "Token invalide"
            else:
                return False, f"HTTP {e.code}"
        except:
            return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)

def validate_token(token):
    """Vérification ultra-rapide du token"""
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v9/users/@me",
            headers={"Authorization": token}
        )
        with urllib.request.urlopen(req, timeout=5):
            return True
    except:
        return False

# ===================================
# SPAM THREAD
# ===================================
def spam_worker():
    global SPAM_RUNNING, CURRENT_TOKEN, CONFIG

    word_index = 0
    while SPAM_RUNNING and CURRENT_TOKEN < len(TOKENS):
        token = TOKENS[CURRENT_TOKEN]
        word = CONFIG["words"][word_index % len(CONFIG["words"])]
        formatted = f"{CONFIG['prefix']}{word}{CONFIG['prefix']}" if CONFIG['prefix'] else word
        ping = f"<@{CONFIG['user_id']}>"
        message = f"{ping} " * CONFIG["pings_per_word"] + formatted

        success, info = send_discord_message(token, CONFIG["channel_id"], message)
        if success:
            CONFIG["sent_count"] += 1
            word_index += 1
            time.sleep(random.uniform(0.011, 0.016))
        else:
            if "Rate limit" in info:
                retry = float(info.split(":")[1].split("s")[0])
                print(f"{Fore.RED}[!] Rate limit ! Attente {retry}s{Style.RESET_ALL}")
                time.sleep(retry)
                CURRENT_TOKEN += 1
            elif "Token invalide" in info:
                print(f"{Fore.RED}[!] Token mort → passage au suivant{Style.RESET_ALL}")
                CURRENT_TOKEN += 1
            else:
                print(f"{Fore.YELLOW}[!] Erreur : {info}{Style.RESET_ALL}")
                time.sleep(1)

    SPAM_RUNNING = False
    print(f"{Fore.MAGENTA}[*] Spam terminé. Total envoyé : {CONFIG['sent_count']}{Style.RESET_ALL}")

# ===================================
# HANDLER HTTP
# ===================================
class CardioHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            status = "En cours" if SPAM_RUNNING else "Arrêté"
            token_snip = TOKENS[CURRENT_TOKEN-1][:15]+"..." if TOKENS and CURRENT_TOKEN > 0 else "N/A"
            data = {
                "status": status,
                "sent": CONFIG["sent_count"],
                "token": token_snip
            }
            self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        global SPAM_RUNNING, SPAM_THREAD, TOKENS, CURRENT_TOKEN, CONFIG

        if self.path == "/start":
            length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(length)
            data = json.loads(post_data)

            # Validation rapide des tokens
            valid_tokens = []
            print(f"{Fore.CYAN}[*] Vérification de {len(data['tokens'])} token(s)...{Style.RESET_ALL}")
            for t in data["tokens"]:
                if validate_token(t):
                    valid_tokens.append(t)
                    print(f"{Fore.GREEN}    Valide{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}    Invalide{Style.RESET_ALL}")
            
            if not valid_tokens:
                self._json_response({"message": "Aucun token valide !", "status": "Échec"})
                return

            TOKENS = valid_tokens
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
                if SPAM_THREAD:
                    SPAM_THREAD.join()

            SPAM_RUNNING = True
            SPAM_THREAD = threading.Thread(target=spam_worker, daemon=True)
            SPAM_THREAD.start()

            self._json_response({
                "message": f"Spam démarré avec {len(TOKENS)} token(s) valide(s) !",
                "status": "En cours"
            })

        elif self.path == "/stop":
            SPAM_RUNNING = False
            self._json_response({"message": "Arrêt en cours..."})

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        return  # Silence logs

# ===================================
# ESTIMATION DURÉE
# ===================================
def print_duration():
    msg_per_sec = 1 / 0.0135
    msg_per_hour = msg_per_sec * 3600
    total_10h = msg_per_hour * 10
    total_20h = msg_per_hour * 20

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN} ESTIMATION DE DURÉE (~74 msg/s)")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}10 heures → ~{total_10h:,.0f} messages")
    print(f"{Fore.YELLOW}20 heures → ~{total_20h:,.0f} messages")
    print(f"{Fore.GREEN}→ Avec 10 pings + mot → spam ultra-dense{Style.RESET_ALL}\n")

# ===================================
# MAIN
# ===================================
def main():
    print(f"{Fore.MAGENTA}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          CARDIO SPAMMER v10.0 - iSH ULTRA-LIGHT          ║")
    print("║       http.server + urllib → 100% natif Python           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")

    print_duration()

    server = socketserver.TCPServer(("127.0.0.1", PORT), CardioHandler)
    print(f"{Fore.GREEN}[+] Serveur local → http://localhost:{PORT}")
    print(f"{Fore.CYAN}[*] Ouvrez votre navigateur → localhost:{PORT}{Style.RESET_ALL}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Arrêt manuel.{Style.RESET_ALL}")

if __name__ == "__main__":
    # === INSTALLATION iSH ===
    # apk add python3
    # (aucun pip requis !)
    main()
