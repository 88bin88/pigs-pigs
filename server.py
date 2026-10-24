# -*- coding: utf-8 -*-
"""
公告看板 - 多电脑协作中转服务器
在【其中一台电脑】上运行: python server.py
其他电脑在公告看板里填: http://<这台电脑的IP>:8123  加入同一组号即可互相同步
数据保存在同目录 notice_server_data.json
"""
import os
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notice_server_data.json")
PORT = int(os.environ.get("PORT", "8123"))
LOCK = threading.Lock()


def load_all():
    with LOCK:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}


def save_all(data):
    with LOCK:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def merge(old, new):
    """合并两组卡片：同一 id 以 ts（毫秒时间戳）新者为准；带 deleted 标记的删除"""
    by_id = {}
    for c in list(old) + list(new):
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        if not cid:
            continue
        ts = c.get("ts", 0)
        if cid not in by_id or ts > by_id[cid].get("ts", 0):
            by_id[cid] = c
    return [c for c in by_id.values() if not c.get("deleted")]


class Handler(BaseHTTPRequestHandler):
    server_version = "NoticeBoardServer/1.0"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/sync":
            q = parse_qs(parsed.query)
            group = q.get("group", ["default"])[0] or "default"
            cards = load_all().get(group, [])
            self._json(200, {"ok": True, "group": group, "cards": cards})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/sync":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            req = json.loads(raw)
            group = req.get("group", "default") or "default"
            cards = req.get("cards", [])
            data = load_all()
            data[group] = merge(data.get(group, []), cards)
            save_all(data)
            self._json(200, {"ok": True, "group": group, "cards": data[group]})
        except Exception as e:
            self._json(400, {"ok": False, "error": str(e)})

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def get_lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    print("=" * 52)
    print("公告看板 · 多电脑协作服务器")
    print("=" * 52)
    print("本机局域网地址: http://%s:%d" % (get_lan_ip(), PORT))
    print("其他电脑在公告看板「协作」面板填这个地址 + 相同组号")
    print("数据文件: %s" % DATA_FILE)
    print("按 Ctrl+C 停止服务")
    print("=" * 52)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
