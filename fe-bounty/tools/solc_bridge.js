const solc = require('/tmp/solcjs/node_modules/solc');
let chunks=[];
process.stdin.on('data',d=>chunks.push(d));
process.stdin.on('end',()=>{
  const input=Buffer.concat(chunks).toString('utf8');
  try { process.stdout.write(solc.compile(input)); }
  catch(e){ process.stderr.write(String(e)); process.exit(1); }
});
