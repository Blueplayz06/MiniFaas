# Mini FaaS: a local serverless platform for studying cold starts and cost

Runs on a laptop with Python 3.9+ and (optionally) Node.js. No Docker, no cloud account.

## What it is
A small Function-as-a-Service platform that mimics the lifecycle of AWS Lambda:
- Each function runs in a **worker process** (our "execution environment").
- **Cold start**: no idle worker exists, so a new one is spawned (process start, runtime start, imports = INIT).
- **Warm start**: an idle worker is reused.
- **Keep-alive**: idle workers are reaped after a timeout.
- **Provisioned workers**: kept warm permanently (like provisioned concurrency).
- **Scale-out**: concurrent requests spawn extra workers.
- **Billing model**: per request + GB-seconds (memory x billed duration), Lambda-style.

## Setup
pip install -r requirements.txt   (matplotlib, numpy, pandas)
Node.js is optional; without it, remove the hello-node lines from server.py and bench_local.py.

## Run
1. Live demo:   python server.py   then open http://localhost:8080
   - Click Invoke (first call is COLD, red), click again (WARM, blue).
   - Burst x10: ten parallel cold starts (scale-out).
   - Kill warm workers: force cold again. Set keep-alive / provisioned and repeat.
2. Measurements:  python bench_local.py        (about 2 to 4 minutes; add --quick for a fast test)
3. Cost model:   python cost_model.py
Outputs (CSV + PNG charts) are written to results/. Use these in the report and slides.

## Experiments
1. Cold vs warm by runtime and package size (light Python, pandas/numpy Python, Node).
2. Same bursty traffic under different keep-alive / provisioned policies: cold-start rate vs worker-seconds held.
3. Concurrent burst: scale-out cold starts for a synchronous API pattern.
4. Break-even between pay-per-use and always-on containers.

## Honest limitations (state these in the report and viva)
- This is a local emulation: cold starts here are process-level, not Firecracker microVM boot plus package download.
- Memory settings are used for billing only; real Lambda also scales CPU with memory, which is not modelled here.
- Prices are assumptions; verify on the AWS pricing page. Results depend on your machine.
- Future work: repeat on AWS Lambda / Azure Functions and compare against these local results.

## Mapping to the seminar
Patterns -> server.py HTTP API (sync) and burst scale-out. Cold start -> exp 1 and 3.
Mitigations -> keep-alive and provisioned workers (exp 2). Cost-performance -> exp 2 and cost_model.py.
