exports.handler = (event) => { let t = 0; for (let i = 0; i < 200000; i++) t += i * i; return { sum: t }; };
