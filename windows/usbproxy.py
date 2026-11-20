import socket, struct, plistlib, threading, sys, os, subprocess, time, ctypes

MUXD = ("127.0.0.1", 27015)   # Apple Mobile Device Service (iTunes / Apple Devices)
PHONE_PORT = 9000             # iPhoneアプリ側のSOCKS5ポート
LOCAL_PORT = 1080             # PC側で開くSOCKS5ポート

def recvn(s, n):
    buf = b""
    while len(buf) < n:
        d = s.recv(n - len(buf))
        if not d:
            raise ConnectionError("closed")
        buf += d
    return buf

def mux_call(s, msg, tag=1):
    msg.update({"ClientVersionString": "usbproxy", "ProgName": "usbproxy"})
    data = plistlib.dumps(msg)
    s.sendall(struct.pack("<IIII", 16 + len(data), 1, 8, tag) + data)
    ln = struct.unpack("<I", recvn(s, 16)[:4])[0]
    return plistlib.loads(recvn(s, ln - 16))

def find_device():
    s = socket.create_connection(MUXD)
    r = mux_call(s, {"MessageType": "ListDevices"})
    s.close()
    for d in r.get("DeviceList", []):
        if d["Properties"].get("ConnectionType") == "USB":
            return d["DeviceID"]
    return None

def open_phone():
    dev = find_device()
    if dev is None:
        raise ConnectionError("iPhoneが見つからない")
    s = socket.create_connection(MUXD)
    r = mux_call(s, {"MessageType": "Connect", "DeviceID": dev,
                     "PortNumber": socket.htons(PHONE_PORT)})
    if r.get("Number") != 0:
        s.close()
        raise ConnectionError("iPhoneアプリに繋がらない(アプリ起動してる?)")
    return s

def pump(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    finally:
        for x in (a, b):
            try: x.shutdown(socket.SHUT_RDWR)
            except OSError: pass

def handle(c):
    try:
        p = open_phone()
    except Exception as e:
        print("ERR:", e)
        c.close()
        return
    threading.Thread(target=pump, args=(c, p), daemon=True).start()
    pump(p, c)
    c.close(); p.close()

def serve():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", LOCAL_PORT))
    srv.listen(128)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()

# ---- DNS(UDP)をSOCKS5経由のTCPに変換 ----
def dns_query(u, q, addr):
    s = None
    try:
        s = socket.create_connection(("127.0.0.1", LOCAL_PORT), timeout=8)
        s.sendall(b"\x05\x01\x00"); recvn(s, 2)
        s.sendall(b"\x05\x01\x00\x01" + socket.inet_aton("1.1.1.1") + struct.pack(">H", 53))
        if recvn(s, 10)[1] != 0:
            return
        s.sendall(struct.pack(">H", len(q)) + q)
        ln = struct.unpack(">H", recvn(s, 2))[0]
        u.sendto(recvn(s, ln), addr)
    except Exception:
        pass
    finally:
        if s: s.close()

def dns_server():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.bind(("127.0.0.1", 53))
    while True:
        q, addr = u.recvfrom(4096)
        threading.Thread(target=dns_query, args=(u, q, addr), daemon=True).start()

def sh(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def base_dir():
    return os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))

def full_mode():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("管理者で実行してね"); input(); return
    t2s = os.path.join(base_dir(), "tun2socks.exe")
    if not os.path.exists(t2s):
        print("tun2socks.exe / wintun.dll を usbproxy.exe の隣に置いてね"); input(); return
    threading.Thread(target=dns_server, daemon=True).start()
    p = subprocess.Popen([t2s, "-device", "tun://usbtun",
                          "-proxy", "socks5://127.0.0.1:%d" % LOCAL_PORT,
                          "-loglevel", "warn"], cwd=base_dir())
    time.sleep(3)
    sh('netsh interface ip set address name="usbtun" source=static addr=10.0.85.2 mask=255.255.255.0 gateway=10.0.85.1 gwmetric=1')
    sh('netsh interface ip set dns name="usbtun" static 127.0.0.1')
    sh('netsh interface ipv4 set interface "usbtun" metric=1')
    print("全通信をiPhone(USB)経由にした。Ctrl+Cで終了(元に戻る)")
    try:
        p.wait()
    except KeyboardInterrupt:
        pass
    finally:
        p.terminate()

def main():
    threading.Thread(target=serve, daemon=True).start()
    print(f"SOCKS5 127.0.0.1:{LOCAL_PORT} -> iPhone(USB):{PHONE_PORT}")
    if "--socks-only" in sys.argv:
        while True: time.sleep(3600)
    full_mode()

if __name__ == "__main__":
    main()
