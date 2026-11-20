"""Mini FaaS platform: worker pool, cold/warm starts, keep-alive reaper, provisioned workers, scale-out, GB-second billing."""
import json, math, os, shutil, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
PRICE_REQ, PRICE_GBS = 0.20 / 1e6, 0.0000166667   # AWS Lambda-style x86 prices (assumption; verify on AWS pricing page)

class Worker:
    def __init__(self, cmd):
        t = time.perf_counter()
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1, cwd=HERE)
        ready = json.loads(self.proc.stdout.readline())
        self.spawn_ms = (time.perf_counter() - t) * 1000     # full cold-start cost: process + runtime + imports
        self.init_ms = ready["init_ms"]
        self.born = time.time(); self.last_used = self.born; self.busy = True; self.provisioned = False
    def call(self, event):
        self.proc.stdin.write(json.dumps(event) + "\n"); self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())
    def kill(self):
        try: self.proc.kill(); self.proc.wait()
        except Exception: pass

class Function:
    def __init__(self, name, path, memory_mb=512, max_concurrency=20, keep_alive=5.0):
        self.name, self.memory_mb, self.max_concurrency, self.keep_alive, self.provisioned = name, memory_mb, max_concurrency, keep_alive, 0
        runner = ["node", "worker.js", path] if path.endswith(".js") else [sys.executable, "worker.py", path]
        self.cmd = runner; self.workers = []; self.pending = 0
        self.stats = dict(invocations=0, cold=0, throttled=0, cost=0.0, lat=[], worker_seconds=0.0)

class Platform:
    def __init__(self):
        self.fns = {}; self.lock = threading.Lock(); self.events = []; self.alive = True
        threading.Thread(target=self._reaper, daemon=True).start()
    def deploy(self, name, path, **kw):
        self.fns[name] = Function(name, os.path.join("functions", path), **kw)
    def _retire(self, fn, w):
        w.kill(); fn.stats["worker_seconds"] += time.time() - w.born
    def _reaper(self):
        while self.alive:
            time.sleep(0.1); now = time.time()
            for fn in self.fns.values():
                with self.lock:
                    dead = [w for w in fn.workers if not w.busy and not w.provisioned and now - w.last_used > fn.keep_alive]
                    for w in dead: fn.workers.remove(w)
                for w in dead: self._retire(fn, w)
    def set_provisioned(self, name, n):
        fn = self.fns[name]; fn.provisioned = n
        with self.lock:
            have = [w for w in fn.workers if w.provisioned]
            for w in have[n:]: w.provisioned = False
            need = max(0, n - len(have)); fn.pending += need
        for _ in range(need):
            w = Worker(fn.cmd); w.provisioned = True; w.busy = False
            with self.lock: fn.workers.append(w); fn.pending -= 1
    def kill_all(self, name):
        fn = self.fns[name]
        with self.lock: ws = [w for w in fn.workers if not w.busy]; [fn.workers.remove(w) for w in ws]
        for w in ws: self._retire(fn, w)
    def shutdown(self):
        self.alive = False
        for fn in self.fns.values():
            for w in list(fn.workers): self._retire(fn, w)
    def invoke(self, name, event=None):
        fn = self.fns[name]; t0 = time.perf_counter(); cold = False
        with self.lock:
            w = next((x for x in fn.workers if not x.busy), None)
            if w: w.busy = True
            elif len(fn.workers) + fn.pending >= fn.max_concurrency:
                fn.stats["throttled"] += 1; return {"error": "throttled", "status": 429}
            else: fn.pending += 1; cold = True
        if cold:
            w = Worker(fn.cmd)
            with self.lock: fn.workers.append(w); fn.pending -= 1
        out = w.call(event or {}); w.last_used = time.time(); w.busy = False
        lat = (time.perf_counter() - t0) * 1000; billed = max(1, math.ceil(out["duration_ms"]))
        cost = PRICE_REQ + (billed / 1000) * (fn.memory_mb / 1024) * PRICE_GBS
        rec = dict(fn=name, cold=cold, latency_ms=round(lat, 1), init_ms=round(w.spawn_ms, 1) if cold else 0, duration_ms=round(out["duration_ms"], 2), billed_ms=billed, cost_usd=cost, ts=time.time())
        with self.lock:
            s = fn.stats; s["invocations"] += 1; s["cold"] += cold; s["cost"] += cost; s["lat"] = (s["lat"] + [rec["latency_ms"]])[-300:]
            self.events = (self.events + [rec])[-40:]
        rec["result"] = out["result"]; return rec
    def snapshot(self):
        with self.lock:
            return {n: dict(memory_mb=f.memory_mb, keep_alive=f.keep_alive, provisioned=f.provisioned, workers=len(f.workers), busy=sum(w.busy for w in f.workers),
                            invocations=f.stats["invocations"], cold=f.stats["cold"], throttled=f.stats["throttled"], cost=f.stats["cost"],
                            recent=f.stats["lat"][-30:]) for n, f in self.fns.items()}, list(self.events[-15:])
