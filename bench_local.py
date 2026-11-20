"""Measured experiments on the mini platform. Usage: python bench_local.py [--quick]"""
import csv, random, sys, time, statistics as st
from concurrent.futures import ThreadPoolExecutor
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import platform_core as pc
Q = "--quick" in sys.argv; COLD_N, WARM_N, SEQ = (5, 30, 20) if Q else (20, 100, 40)
def pct(v, p): v = sorted(v); return v[min(len(v) - 1, int(p / 100 * len(v)))]
FN = [("hello-py", "fn_light.py"), ("heavy-py", "fn_heavy.py"), ("hello-node", "fn_node.js")]

# Experiment 1: cold vs warm per function (runtime and package-size effect)
p = pc.Platform(); rows = []
for n, f in FN: p.deploy(n, f, keep_alive=60)
for n, _ in FN:
    for _ in range(COLD_N):
        p.kill_all(n); r = p.invoke(n); rows.append([n, "cold", r["latency_ms"], r["init_ms"], r["duration_ms"], r["billed_ms"]])
    for _ in range(WARM_N):
        r = p.invoke(n); rows.append([n, "warm", r["latency_ms"], 0, r["duration_ms"], r["billed_ms"]])
p.shutdown()
with open("results/exp1_cold_vs_warm.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["function", "kind", "latency_ms", "cold_overhead_ms", "handler_ms", "billed_ms"]); w.writerows(rows)
print("\nEXP1 cold vs warm (ms)\nfunction      kind   p50     p95     p99")
tab = {}
for n, _ in FN:
    for k in ("cold", "warm"):
        v = [r[2] for r in rows if r[0] == n and r[1] == k]; tab[(n, k)] = (pct(v, 50), pct(v, 95), pct(v, 99))
        print(f"{n:<13} {k:<5} {tab[(n,k)][0]:7.1f} {tab[(n,k)][1]:7.1f} {tab[(n,k)][2]:7.1f}")
x = range(len(FN)); plt.figure(figsize=(8, 5))
plt.bar([i - .2 for i in x], [tab[(n, "cold")][0] for n, _ in FN], .4, label="cold p50", color="#d9534f")
plt.bar([i + .2 for i in x], [tab[(n, "warm")][0] for n, _ in FN], .4, label="warm p50", color="#2f5597")
plt.xticks(list(x), [n for n, _ in FN]); plt.ylabel("latency (ms)"); plt.title("Cold vs warm latency by runtime / package size"); plt.legend(); plt.tight_layout(); plt.savefig("results/fig1_cold_vs_warm.png", dpi=150); plt.close()

# Experiment 2: keep-alive / provisioned workers - cold-start rate vs resources held (the cost-performance trade-off)
random.seed(1); gaps = [random.choice([0.05, 0.1, 0.3, 1.5, 3.0]) for _ in range(SEQ)]
cfgs = [("keep-alive 0.3s", 0.3, 0), ("keep-alive 1s", 1.0, 0), ("keep-alive 5s", 5.0, 0), ("provisioned x1", 1.0, 1)]; res = []
print("\nEXP2 same bursty traffic, different warm-keeping policy")
for label, ka, prov in cfgs:
    p = pc.Platform(); p.deploy("hello-py", "fn_light.py", keep_alive=ka)
    if prov: p.set_provisioned("hello-py", prov)
    t0 = time.time(); lat = []; cold = 0
    for g in gaps:
        time.sleep(g); r = p.invoke("hello-py"); lat.append(r["latency_ms"]); cold += r["cold"]
    fn = p.fns["hello-py"]; now = time.time()
    held = fn.stats["worker_seconds"] + sum(now - w.born for w in fn.workers); p.shutdown()
    res.append((label, 100 * cold / SEQ, st.mean(lat), pct(lat, 95), held))
    print(f"{label:<16} cold {100*cold/SEQ:5.1f}%  mean {st.mean(lat):6.1f} ms  p95 {pct(lat,95):6.1f} ms  worker-seconds held {held:5.1f}")
with open("results/exp2_keepalive.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["policy", "cold_pct", "mean_ms", "p95_ms", "worker_seconds"]); w.writerows(res)
fig, a = plt.subplots(figsize=(8, 5)); a.scatter([r[4] for r in res], [r[1] for r in res], s=120, color="#2f5597")
for r in res: a.annotate(r[0], (r[4], r[1]), textcoords="offset points", xytext=(6, 6))
a.set_xlabel("worker-seconds held (idle resource cost)"); a.set_ylabel("cold-start rate (%)"); a.set_title("Latency vs resource trade-off"); plt.tight_layout(); plt.savefig("results/fig2_keepalive_tradeoff.png", dpi=150); plt.close()

# Experiment 3: concurrent burst (scale-out) - synchronous API pattern
p = pc.Platform(); p.deploy("hello-py", "fn_light.py", keep_alive=30); K = 10; out = {}
for label in ("burst 1 (no warm workers)", "burst 2 (warm workers exist)"):
    with ThreadPoolExecutor(K) as ex: rs = list(ex.map(lambda _: p.invoke("hello-py"), range(K)))
    out[label] = sorted(r["latency_ms"] for r in rs); print(f"\nEXP3 {label}: cold {sum(r['cold'] for r in rs)}/{K}, median {st.median(out[label]):.1f} ms, max {out[label][-1]:.1f} ms")
p.shutdown(); plt.figure(figsize=(8, 5))
for (l, v), c in zip(out.items(), ["#d9534f", "#2f5597"]): plt.plot(range(1, K + 1), v, "o-", label=l, color=c)
plt.xlabel("request (sorted by latency)"); plt.ylabel("latency (ms)"); plt.title(f"{K} concurrent requests: scale-out cold starts"); plt.legend(); plt.tight_layout(); plt.savefig("results/fig3_burst.png", dpi=150)
print("\nCharts and CSVs saved in results/")
