# -*- coding: utf-8 -*-
"""
CARDIO SPAMMER v9.0 - iSH NATIVE
SANS discord.py → API HTTP Discord pure (requests)
Interface Web (aiohttp) - Zéro lazy loading
Ping ID utilisateur personnalisé + prefix Markdown
Spam ultra-rapide avec rotation de tokens
"""

import aiohttp
from aiohttp import web
import asyncio
import threading
import random
import time
import json
import os
from colorama import init, Fore, Style

init(autoreset=True)

# ===================================
# VARIABLES GLOBALES
# ===================================
SPAM_TASK = None
TOKENS = []
CURRENT_TOKEN_INDEX = 0
CONFIG = {
    "channel_id": None,
    "words": [],
    "user_id": None,           # ID de la personne à ping
    "pings_per_word": 10,
    "prefix": "",
    "delay_min": 0.011,
    "delay_max": 0.016,
    "running": False,
    "sent_count": 0
}
SESSION = None

# ===================================
# SERVEUR WEB (aiohttp)
# ===================================
async def index(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cardio Spammer v9.0 - iSH</title>
        <meta charset="utf-8">
        <style>
            body { font-family: 'Courier New', monospace; background: #000; color: #0f0; padding: 20px; }
            h1 { color: #0f0; text-align: center; }
            .container { max-width: 800px; margin: 0 auto; background: #111; padding: 20px; border: 2px solid #0f0; border-radius: 10px; }
            input, textarea, button { width: 100%; padding: 12px; margin: 10px 0; font-size: 16px; background: #222; color: #0f0; border: 1px solid #0f0; border-radius: 5px; }
            button { background: #0f0; color: #000; font-weight: bold; cursor: pointer; }
            button:hover { background: #0c0; }
            button.stop { background: #f00; }
            .status { margin: 20px 0; padding: 15px; background: #222; border-left: 5px solid #0f0; font-size: 18px; }
            .log { height: 250px; overflow-y: auto; background: #000; padding: 10px; border: 1px solid #0f0; font-size: 14px; color: #0f0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>CARDIO SPAMMER v9.0 - iSH NATIVE</h1>
            <div class="status" id="status">Status: En attente...</div>
            
            <label>ID du Salon Discord</label>
            <input type="text" id="channel_id" placeholder="123456789012345678">

            <label>ID de la personne à ping</label>
            <input type="text" id="user_id" placeholder="123456789012345678">

            <label>Tokens (un par ligne)</label>
            <textarea id="tokens" rows="4" placeholder="token1\ntoken2"></textarea>

            <label>Mots (un par ligne)</label>
            <textarea id="words" rows="6" placeholder="Je\nSuis\nTon\nPere"></textarea>

            <label>Pings par message (défaut: 10)</label>
            <input type="number" id="pings_per_word" value="10" min="1">

            <label>Préfixe Markdown (ex: **, ||, __)</label>
            <input type="text" id="prefix" placeholder="** pour gras">

            <button onclick="startSpam()">DÉMARRER LE SPAM</button>
            <button onclick="stopSpam()" class="stop">ARRÊTER</button>

            <div class="log" id="log"></div>
        </div>

        <script>
            function log(msg) {
                const log = document.getElementById('log');
                const time = new Date().toLocaleTimeString();
                log.innerHTML += `<div>[${time}] ${msg}</div>`;
                log.scrollTop = log.scrollHeight;
            }

            async function startSpam() {
                const data = {
                    channel_id: document.getElementById('channel_id').value.trim(),
                    user_id: document.getElementById('user_id').value.trim(),
                    tokens: document.getElementById('tokens').value.trim().split('\\n').filter(t => t.trim()),
                    words: document.getElementById('words').value.trim().split('\\n').filter(w => w.trim()),
                    pings_per_word: parseInt(document.getElementById('pings_per_word').value) || 10,
                    prefix: document.getElementById('prefix').value
                };

                if (!data.channel_id || !data.user_id || !data.tokens.length || !data.words.length) {
                    alert("Tous les champs obligatoires !");
                    return;
                }

                document.getElementById('status').innerText = "Status: Démarrage...";
                const res = await fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                log(result.message);
            }

            async function stopSpam() {
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
    return web.Response(text=html, content_type='text/html')

# ===================================
# API HANDLERS
# ===================================
async def start_spam(request):
    global SPAM_TASK, TOKENS, CURRENT_TOKEN_INDEX, CONFIG, SESSION
    data = await request.json()

    CONFIG.update({
        "channel_id": data["channel_id"],
        "user_id": data["user_id"],
        "words": data["words"],
        "pings_per_word": data["pings_per_word"],
        "prefix": data["prefix"],
        "running": True,
        "sent_count": 0
    })
    TOKENS = data["tokens"]
    CURRENT_TOKEN_INDEX = 0

    if SPAM_TASK and not SPAM_TASK.done():
        SPAM_TASK.cancel()

    if not SESSION or SESSION.closed:
        SESSION = aiohttp.ClientSession()

    SPAM_TASK = asyncio.create_task(spam_controller())
    return web.json_response({"message": "Spam lancé avec API HTTP !"})

async def stop_spam(request):
    global SPAM_TASK, CONFIG
    CONFIG["running"] = False
    if SPAM_TASK:
        SPAM_TASK.cancel()
    return web.json_response({"message": "Spam arrêté."})

async def get_status(request):
    global CONFIG, CURRENT_TOKEN_INDEX, TOKENS
    return web.json_response({
        "status": "En cours" if CONFIG["running"] else "Arrêté",
        "sent": CONFIG["sent_count"],
        "token": TOKENS[CURRENT_TOKEN_INDEX-1][:15] + "..." if TOKENS and CURRENT_TOKEN_INDEX > 0 else "N/A"
    })

# ===================================
# SPAM VIA API HTTP DISCORD
# ===================================
async def send_message(token, channel_id, content):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
    }
    payload = {"content": content}

    try:
        async with SESSION.post(url, json=payload, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                return True, None
            elif resp.status == 429:
                retry_after = (await resp.json()).get("retry_after", 1)
                return False, f"Rate limit: {retry_after}s"
            elif resp.status in (401, 403):
                return False, "Token invalide"
            else:
                text = await resp.text()
                return False, f"HTTP {resp.status}: {text[:100]}"
    except Exception as e:
        return False, str(e)

# ===================================
# SPAM CONTROLLER
# ===================================
async def spam_controller():
    global CURRENT_TOKEN_INDEX, CONFIG, SESSION

    while CONFIG["running"] and CURRENT_TOKEN_INDEX < len(TOKENS):
        token = TOKENS[CURRENT_TOKEN_INDEX]
        print(f"{Fore.GREEN}[+] Utilisation token {CURRENT_TOKEN_INDEX+1}/{len(TOKENS)}{Style.RESET_ALL}")

        word_index = 0
        local_sent = 0

        while CONFIG["running"] and CURRENT_TOKEN_INDEX < len(TOKENS):
            word = CONFIG["words"][word_index % len(CONFIG["words"])]
            formatted = f"{CONFIG['prefix']}{word}{CONFIG['prefix']}" if CONFIG["prefix"] else word
            ping = f"<@{CONFIG['user_id']}>"
            ping_part = f"{ping} " * CONFIG["pings_per_word"]
            message = ping_part + formatted

            success, error = await send_message(token, CONFIG["channel_id"], message)
            if success:
                CONFIG["sent_count"] += 1
                local_sent += 1
                word_End_index += 1
                delay = random.uniform(CONFIG["delay_min"], CONFIG["delay_max"])
                await asyncio.sleep(delay)
            else:
                if "Rate limit" in error:
                    retry = float(error.split(":")[1].split("s")[0])
                    print(f"{Fore.RED}[!] Rate limit ! Attente {retry}s...{Style.RESET_ALL}")
                    await asyncio.sleep(retry)
                    break  # Switch token
                elif "Token invalide" in error:
                    print(f"{Fore.RED}[!] Token mort. Passage au suivant.{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.YELLOW}[!] Erreur : {error}{Style.RESET_ALL}")
                    await asyncio.sleep(1)

        CURRENT_TOKEN_INDEX += 1

    CONFIG["running"] = False
    print(f"{Fore.MAGENTA}[*] Spam terminé. Total : {CONFIG['sent_count']} messages.{Style.RESET_ALL}")

# ===================================
# ESTIMATION DURÉE
# ===================================
def print_duration_estimate(word_count, pings_per_word):
    msg_per_sec = 1 / 0.0135
    msg_per_hour = msg_per_sec * 3600
    total_10h = msg_per_hour * 10
    total_20h = msg_per_hour * 20
    cycles_10h = total_10h // word_count
    cycles_20h = total_20h // word_count

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN} ESTIMATION DE DURÉE (~74 msg/s)")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}10 heures → ~{total_10h:,.0f} messages → {cycles_10h:,.0f} cycles")
    print(f"{Fore.YELLOW}20 heures → ~{total_20h:,.0f} messages → {cycles_20h:,.0f} cycles")
    print(f"{Fore.GREEN}→ 1 cycle = {word_count} mots → {word_count} messages{Style.RESET_ALL}\n")

# ===================================
# MAIN
# ===================================
async def main():
    print(f"{Fore.MAGENTA}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           CARDIO SPAMMER v9.0 - iSH NATIVE API           ║")
    print("║          API HTTP Discord | aiohttp | Zéro discord.py    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")

    print_duration_estimate(4, 10)

    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/start', start_spam)
    app.router.add_post('/stop', stop_spam)
    app.router.add_get('/status', get_status)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    print(f"{Fore.GREEN}[+] Serveur web → http://<IP-iSH>:8080")
    print(f"{Fore.CYAN}[*] Interface prête. Configurez via navigateur.{Style.RESET_ALL}\n")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    # === INSTALLATION iSH ===
    # apk add python3 py3-pip
    # pip install aiohttp colorama
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Arrêt manuel.{Style.RESET_ALL}")
