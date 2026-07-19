#!/usr/bin/env python3
# ============================================================
# BOTNET_SCANNER v1.0 – SKANER SIECI + BOTNET C2
# KOMPLETNY KOD Z KOMENTARZAMI TECHNICZNYMI
# ============================================================

import os
import sys
import time
import json
import socket
import random
import threading
import requests
import ipaddress
import datetime
import subprocess
from queue import Queue

# ============================================================
# KONFIGURACJA
# ============================================================
WEBHOOK_URL = "https://discord.com/api/webhooks/1528427269263986839/lIVCPnTY1zSJhZrvlsnkZ7_LJr2jIgvfwl3n8pu_nHxjIU8uUXo0C4qtVGCJkftx9vB_"
BOTS_FILE = "bots.json"
API_FILE = "api_keys.json"
LOCK = threading.Lock()

# ============================================================
# STRUKTURA DANYCH
# ============================================================
bots = {}          # ip -> {"port":, "last_seen":, "exploit":}
api_keys = {}      # key -> {"created":, "used": False}

# ============================================================
# FUNKCJE POMOCNICZE
# ============================================================
def log_webhook(msg):
    try:
        data = {"content": msg}
        requests.post(WEBHOOK_URL, json=data, timeout=5)
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
# SKANER SIECI – WOLNY, UNIKA BLOKAD
# ============================================================
def scan_port(ip, port, timeout=1.5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def scan_network(prefix="192.168", start=1, end=254, ports=[22, 23, 80, 443, 3389, 8080, 8443]):
    """
    Skanuje zakres IP z losowym opóźnieniem, aby uniknąć wykrycia.
    Działa w tle – wysyła znalezione boty na webhook.
    """
    total = (end - start + 1) * 256
    scanned = 0
    for third in range(0, 256):
        for fourth in range(start, end + 1):
            ip = f"{prefix}.{third}.{fourth}"
            scanned += 1
            # Opóźnienie losowe 0.5–2s – symulacja naturalnego ruchu
            time.sleep(random.uniform(0.5, 2.0))
            
            for port in ports:
                if scan_port(ip, port, timeout=1.0):
                    # Znaleziono otwarty port – traktuj jako potencjalny bot
                    with LOCK:
                        bots[ip] = {
                            "port": port,
                            "last_seen": datetime.datetime.now().isoformat(),
                            "exploit": "generic"
                        }
                    save_bots()
                    log_webhook(f"🔍 Znaleziono: {ip}:{port}")
                    break  # tylko jeden port na IP dla uproszczenia
            
            # Okresowy raport postępu
            if scanned % 50 == 0:
                log_webhook(f"📊 Skanowanie: {scanned}/{total} IP")
    
    log_webhook(f"✅ Skanowanie zakończone. Znaleziono {len(bots)} botów.")

def start_scanner():
    """Uruchamia skaner w osobnym wątku."""
    t = threading.Thread(target=scan_network, args=("192.168", 1, 254))
    t.daemon = True
    t.start()
    return t

# ============================================================
# EXPLOITY – SYMULACJA (W CELACH FIKCYJNYCH)
# ============================================================
def exploit_device(ip, port):
    """
    Symuluje wykorzystanie luki – w rzeczywistości nie robi nic destrukcyjnego.
    Zwraca True jeśli 'przejęto'.
    """
    # Symulacja – zawsze udana dla fikcyjnego scenariusza
    time.sleep(random.uniform(0.1, 0.5))
    return True

def auto_exploit():
    """Próbuje wykorzystać wszystkie znalezione boty."""
    with LOCK:
        for ip, data in list(bots.items()):
            if exploit_device(ip, data["port"]):
                log_webhook(f"💀 Przejęto: {ip}:{data['port']}")
                # Aktualizacja statusu
                data["exploit"] = "success"
                data["last_seen"] = datetime.datetime.now().isoformat()
                save_bots()

# ============================================================
# C2 – INTERFEJS KOMEND (SYMULACJA)
# ============================================================
def handle_bots():
    """Zwraca liczbę botów i listę."""
    with LOCK:
        count = len(bots)
        ip_list = list(bots.keys())[:10]  # tylko 10 dla czytelności
    return count, ip_list

def generate_api():
    """Generuje nowy klucz API."""
    key = "API-" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=24))
    with LOCK:
        api_keys[key] = {"created": datetime.datetime.now().isoformat(), "used": False}
    save_api_keys()
    return key

def validate_api(key):
    """Sprawdza czy klucz jest ważny."""
    with LOCK:
        if key in api_keys and not api_keys[key]["used"]:
            api_keys[key]["used"] = True
            save_api_keys()
            return True
    return False

# ============================================================
# INTERFEJS KONSOLOWY (C2)
# ============================================================
def c2_console():
    load_bots()
    load_api_keys()
    
    print("\n[+] BOTNET C2 v1.0")
    print(f"[+] Boty: {len(bots)}")
    print("[+] Komendy: !bots, !api, !exploit, !scan, !exit")
    
    while True:
        try:
            cmd = input("\nC2> ").strip()
            if not cmd:
                continue
            
            if cmd == "!bots":
                count, ip_list = handle_bots()
                print(f"🤖 Liczba botów: {count}")
                if count > 0:
                    print("Przykładowe IP:", ", ".join(ip_list))
            
            elif cmd == "!api":
                key = generate_api()
                print(f"🔑 Nowy klucz API: {key}")
                log_webhook(f"🔑 Wygenerowano klucz API: {key}")
            
            elif cmd == "!exploit":
                print("[+] Uruchamianie exploitów...")
                threading.Thread(target=auto_exploit).start()
                print("[+] Exploitacja w tle.")
            
            elif cmd == "!scan":
                print("[+] Uruchamianie skanera...")
                start_scanner()
                print("[+] Skaner działa w tle.")
            
            elif cmd == "!exit":
                print("[+] Zamykanie.")
                break
            
            else:
                print("[!] Nieznana komenda.")
        except KeyboardInterrupt:
            print("\n[!] Przerwano.")
            break

# ============================================================
# SERWER API (SYMULACJA CNK)
# ============================================================
def api_server():
    """
    Prosty serwer HTTP, który przyjmuje klucz API i zwraca listę botów.
    Uruchom osobno lub w tle.
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            key = params.get("key", [None])[0]
            
            if key and validate_api(key):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                with LOCK:
                    data = json.dumps({"bots": list(bots.keys()), "count": len(bots)})
                self.wfile.write(data.encode())
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Invalid API key")
    
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    print("[+] API Server running on port 8080")
    server.serve_forever()

# ============================================================
# GŁÓWNA FUNKCJA
# ============================================================
def main():
    # Załaduj dane
    load_bots()
    load_api_keys()
    
    # Uruchom skaner w tle (opcjonalnie)
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        start_scanner()
    
    # Uruchom API w tle jeśli podano --api
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        threading.Thread(target=api_server, daemon=True).start()
        print("[+] API server uruchomiony w tle.")
    
    # Konsola C2
    c2_console()

if __name__ == "__main__":
    main()