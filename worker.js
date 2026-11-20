const t = process.hrtime.bigint(); const mod = require(require('path').resolve(process.argv[2]));
console.log(JSON.stringify({ ready: true, init_ms: Number(process.hrtime.bigint() - t) / 1e6 }));
require('readline').createInterface({ input: process.stdin }).on('line', (l) => {
  const s = process.hrtime.bigint(); const res = mod.handler(JSON.parse(l), {});
  console.log(JSON.stringify({ result: res, duration_ms: Number(process.hrtime.bigint() - s) / 1e6 }));
});
