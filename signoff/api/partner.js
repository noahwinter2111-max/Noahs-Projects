// Signoff partner gateway. Every partner is a PLACEHOLDER until its keys are set in Vercel.
// GET  /api/partner                      -> status of every partner (configured or placeholder, which env vars it needs)
// POST /api/partner {partner, action, args} -> 503 { error: "not_configured" } until that partner's keys exist; then the real call.
const crypto = require('crypto');
const PARTNERS = {
  bank:      { name: 'Partner bank (Column)',        env: ['COLUMN_API_KEY', 'COLUMN_WEBHOOK_SECRET'], base: 'https://api.column.com' },
  formation: { name: 'Formation partner',            env: ['FORMATION_API_KEY'] },
  identity:  { name: 'Identity partner (bank-side)', env: ['IDENTITY_API_KEY'] },
  books:     { name: 'QuickBooks Online',            env: ['QBO_CLIENT_ID', 'QBO_CLIENT_SECRET'] },
  email:     { name: 'Gmail / Microsoft 365',        env: ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'] },
  esign:     { name: 'E-signature partner',          env: ['ESIGN_API_KEY'] },
  travel:    { name: 'Travel partner',               env: ['TRAVEL_API_KEY'] }
};
const configured = p => PARTNERS[p].env.every(k => !!process.env[k]);
function body(req){ if (!req.body) return {}; if (typeof req.body === 'string') { try { return JSON.parse(req.body); } catch (e) { return {}; } } return req.body; }

// ---- Column (sponsor bank) scaffolding. Paths follow docs.column.com; confirm each against the sandbox before go-live.
async function column(path, method, data){
  const r = await fetch(PARTNERS.bank.base + path, { method, headers: { Authorization: 'Basic ' + Buffer.from(process.env.COLUMN_API_KEY + ':').toString('base64'), 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : undefined });
  const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.message || ('column ' + r.status)); return j;
}
const BANK = {
  // open_account: create the business entity from the formation documents, then a checking account under it
  open_account: async a => { const ent = await column('/entities/business', 'POST', { business_name: a.name, ein: a.ein, registration_state: a.state, beneficial_owners: a.owners || [] }); const acct = await column('/bank-accounts', 'POST', { entity_id: ent.id, description: a.name + ' checking' }); return { entity_id: ent.id, account_id: acct.id, status: 'pending_kyc' }; },
  balance:      async a => column('/bank-accounts/' + encodeURIComponent(a.account_id), 'GET'),
  transactions: async a => column('/transfers?bank_account_id=' + encodeURIComponent(a.account_id) + '&limit=25', 'GET'),
  pay:          async a => { const cp = await column('/counterparties', 'POST', { name: a.payee, routing_number: a.routing, account_number: a.account }); return column('/transfers/ach', 'POST', { bank_account_id: a.account_id, counterparty_id: cp.id, amount: Math.round(a.amount * 100), currency_code: 'USD', description: a.memo || '', type: 'CREDIT' }); },
  issue_card:   async a => column('/cards', 'POST', { bank_account_id: a.account_id, description: a.name, spending_limit: Math.round(a.limit * 100) })
};

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store'); res.setHeader('Access-Control-Allow-Origin', '*'); res.setHeader('Access-Control-Allow-Headers', 'Content-Type'); res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET') { const out = {}; for (const p in PARTNERS) out[p] = { name: PARTNERS[p].name, configured: configured(p), placeholder: !configured(p), needs: PARTNERS[p].env }; return res.status(200).json({ partners: out, ai: { configured: !!process.env.ANTHROPIC_API_KEY, needs: ['ANTHROPIC_API_KEY'] } }); }
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST' });
  const { partner, action, args } = body(req);
  if (!PARTNERS[partner]) return res.status(400).json({ error: 'unknown partner' });
  if (!configured(partner)) return res.status(503).json({ error: 'not_configured', partner, name: PARTNERS[partner].name, needs: PARTNERS[partner].env, message: PARTNERS[partner].name + ' is a placeholder until its keys are added to the server.' });
  try {
    if (partner === 'bank') { if (!BANK[action]) return res.status(400).json({ error: 'unknown action' }); return res.status(200).json(await BANK[action](args || {})); }
    return res.status(501).json({ error: 'not_implemented', message: PARTNERS[partner].name + ' has keys but no integration code yet.' });
  } catch (e) { return res.status(502).json({ error: 'upstream', message: String(e.message || e).slice(0, 300) }); }
};
module.exports.verifyColumnWebhook = (rawBody, signature) => { const s = process.env.COLUMN_WEBHOOK_SECRET; if (!s) return false; const h = crypto.createHmac('sha256', s).update(rawBody).digest('hex'); return !!signature && crypto.timingSafeEqual(Buffer.from(h), Buffer.from(String(signature))); };
