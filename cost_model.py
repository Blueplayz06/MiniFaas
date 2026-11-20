"""Break-even: pay-per-use serverless vs always-on containers. Prices are ASSUMPTIONS - verify on AWS pricing page."""
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, numpy as np
PRICE_REQ, PRICE_GBS = 0.20 / 1e6, 0.0000166667
DUR_S, MEM_GB = 0.100, 0.5; CONTAINER = 2 * 0.0208 * 730; SEC = 30 * 24 * 3600
per = PRICE_REQ + DUR_S * MEM_GB * PRICE_GBS; be = CONTAINER / (SEC * per)
print(f"cost/request ${per:.7f} | containers ${CONTAINER:.2f}/month | break-even ~{be:.1f} req/s")
r = np.linspace(0, 3 * be, 200); plt.figure(figsize=(8, 5)); plt.plot(r, r * SEC * per, label="Serverless (pay per use)", color="#2f5597")
plt.axhline(CONTAINER, color="#d9534f", label="Containers (fixed)"); plt.axvline(be, ls=":", color="grey")
plt.xlabel("sustained requests per second"); plt.ylabel("USD per month"); plt.title(f"Break-even ~{be:.0f} req/s"); plt.legend(); plt.tight_layout(); plt.savefig("results/fig4_breakeven.png", dpi=150)
