const { get, put } = require('@vercel/blob');
const PATH = 'waitlist/list.json', ADMIN = process.env.WAITLIST_ADMIN || '';
async function readList(){ const r = await get(PATH, { access: 'private', useCache: false }); if (!r) return []; try { return JSON.parse(await new Response(r.stream).text()) || []; } catch (e) { return []; } }
async function writeList(list){ await put(PATH, JSON.stringify(list), { access: 'private', addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json' }); }
function body(req){ if (!req.body) return {}; if (typeof req.body === 'string') { try { return JSON.parse(req.body); } catch (e) { return {}; } } return req.body; }
module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store'); res.setHeader('Access-Control-Allow-Origin', '*'); res.setHeader('Access-Control-Allow-Headers', 'Content-Type'); res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET') {
    const key = (req.query && req.query.key) || '';
    if (!ADMIN || key !== ADMIN) return res.status(404).end();
    try {
      let list = await readList();
      if (req.query.remove) { list = list.filter(x => x.email !== String(req.query.remove).toLowerCase()); await writeList(list); }
      list = list.slice().reverse();
      if (req.query.format === 'csv') { res.setHeader('Content-Type', 'text/csv'); return res.status(200).send('email,what,when\n' + list.map(x => [x.email, x.why, x.at].map(v => '"' + String(v || '').replace(/"/g, '""') + '"').join(',')).join('\n')); }
      return res.status(200).json({ count: list.length, list });
    } catch (e) { return res.status(500).json({ error: 'store', detail: String(e.message || e) }); }
  }
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST' });
  const b = body(req); const email = String(b.email || '').trim().toLowerCase().slice(0, 120); const why = String(b.why || '').trim().slice(0, 200);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return res.status(400).json({ error: 'bad email' });
  try {
    const list = await readList(); const seen = list.some(x => x.email === email);
    if (!seen) { list.push({ email, why, at: new Date().toISOString() }); await writeList(list); }
    return res.status(200).json({ ok: true, new: !seen });
  } catch (e) { return res.status(500).json({ error: 'store', detail: String(e.message || e) }); }
};
