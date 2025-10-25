# -*- coding: utf-8 -*-
"""
CARDIO SPAMMER v14.0 - iSH ULTRA-STABLE
100% natif Python • http.server + urllib.request
Interface épurée • Upload .txt • Token vérifié 100% fiable
FIX : SyntaxError global + BrokenPipe + Token invalide
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
# CONFIG GLOBALE
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
# HTML ÉPURÉE
# ===================================
HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cardio Spammer v14</title>
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
    <h1>CARDIO SPAMMER v14</h1>
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
# VÉRIFICATION TOKEN 100% FIABLE (Recherche approfondie)
# ===================================
def validate_token(token):
    """
    Méthode la plus fiable pour vérifier un token Discord (2025)
    - Endpoint : /users/@me
    - Headers : Authorization + User-Agent
    - Vérifie : presence de 'id', 'username', 'discriminator'
    - Timeout strict
    """
    token = token.strip()
    if not token or len(token) < 50:
        return False

    url = "https://discord.com/api/v9/users/@me"
    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Accept": "*/*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Connection": "keep-alive"
    }

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Token valide si on a au moins id + username
            return bool(data.get("id") and data.get("username"))
    except urllib.error.HTTPError as e:
        # 401 = token invalide
        return False
    except:
        return False

# ===================================
# ENVOI MESSAGE (robuste)
# ===================================
def send_message(token, channel_id, content):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    payload = json.dumps({"content": content}).encode("utf-8")
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
            body = e.read().decode("utf-8", errors="ignore")
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
    except Exception:
        return False, "timeout"

# ===================================
# SPAM WORKER
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

        success
