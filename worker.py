"""Worker process = one 'execution environment'. INIT: start interpreter + import function. Then serve invocations."""
import sys, json, time, importlib.util
t = time.perf_counter()
spec = importlib.util.spec_from_file_location("fn", sys.argv[1]); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(json.dumps({"ready": True, "init_ms": (time.perf_counter() - t) * 1000}), flush=True)
for line in sys.stdin:
    s = time.perf_counter(); res = mod.handler(json.loads(line), {})
    print(json.dumps({"result": res, "duration_ms": (time.perf_counter() - s) * 1000}), flush=True)
