"""Run: python server.py  -> open http://localhost:8080  (live dashboard + HTTP API: GET /invoke/<fn>)"""
import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from platform_core import Platform
P = Platform()
P.deploy("hello-py", "fn_light.py", memory_mb=512, keep_alive=5)
P.deploy("heavy-py", "fn_heavy.py", memory_mb=512, keep_alive=5)
P.deploy("hello-node", "fn_node.js", memory_mb=512, keep_alive=5)
PAGE = open("dashboard.html", encoding="utf-8").read()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query); parts = u.path.strip("/").split("/")
        if u.path == "/": return self.send(200, PAGE, "text/html; charset=utf-8")
        if u.path == "/stats":
            f, e = P.snapshot(); return self.send(200, json.dumps({"functions": f, "events": e}))
        if parts[0] == "invoke" and len(parts) == 2 and parts[1] in P.fns:
            r = P.invoke(parts[1]); return self.send(429 if "error" in r else 200, json.dumps(r))
        if parts[0] == "kill" and parts[1] in P.fns: P.kill_all(parts[1]); return self.send(200, "{}")
        if parts[0] == "config" and parts[1] in P.fns:
            fn = P.fns[parts[1]]
            if "keep_alive" in q: fn.keep_alive = float(q["keep_alive"][0])
            if "provisioned" in q: threading.Thread(target=P.set_provisioned, args=(parts[1], int(q["provisioned"][0]))).start()
            return self.send(200, "{}")
        self.send(404, '{"error":"not found"}')
if __name__ == "__main__":
    print("Mini FaaS running on http://localhost:8080  (Ctrl+C to stop)")
    try: ThreadingHTTPServer(("127.0.0.1", 8080), H).serve_forever()
    except KeyboardInterrupt: P.shutdown()
