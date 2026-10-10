// Signoff as a gate for ANY agent. A third-party agent (CoFounder, ChatGPT, a script) proposes an action here;
// Signoff decides its tier and what it needs, records it, and the owner approves it in the Signoff app.
//
// POST /api/propose {owner, agent, action, args, state?}  -> {decision, tier, reason, proposal_id, approve_url}
//   decision: "run" (tier 0-1, allowed), "approval_required" (tier 2), "code_required" (tier 3), "refused"
// GET  /api/propose?owner=…                               -> the owner's recent proposals and their outcomes
// The agent never gets a key to the bank, the filer, QuickBooks or email. It only ever gets a decision.
const crypto = require('crypto');
const { readOwner, writeOwner } = require('./partner.js');
const SITE = process.env.SIGNOFF_SITE || 'https://signoff-three.vercel.app';
const TOOLS = {
  get_state: 0, get_balance: 0, list_inbox: 0, tax_calendar: 0, pl_report: 0, list_documents: 0, spend_summary: 0, cap_table: 0, runway: 0,
  draft_email: 1, add_investor: 1,
  start_identity_check: 2, file_formation: 2, apply_ein: 2, send_docs_to_bank: 2, connect_books: 2, connect_email: 2, send_invoice: 2, reply_email: 2, send_contract: 2, issue_card: 2, convert_to_corp: 2, issue_safe: 2, share_data_room: 2, send_investor_update: 2,
  pay: 3, book_travel: 3, schedule_payment: 3, set_aside_tax: 3
};
const NEEDS = { file_formation: ['identity'], apply_ein: ['filed'], send_docs_to_bank: ['ein'], connect_books: ['bank'], send_invoice: ['books'], pay: ['bank'], book_travel: ['bank'], schedule_payment: ['bank'], set_aside_tax: ['bank'], issue_card: ['bank'], reply_email: ['mail'], send_investor_update: ['mail'], issue_safe: ['bank', 'corp'] };
function body(req){ if (!req.body) return {}; if (typeof req.body === 'string') { try { return JSON.parse(req.body); } catch (e) { return {}; } } return req.body; }
// The same rules the app enforces, run server-side so no agent can skip them.
function gate(action, args, st){
  if (!(action in TOOLS)) return { refused: 'Unknown action. Signoff only signs actions it knows.' };
  for (const n of (NEEDS[action] || [])) {
    if (n === 'identity' && !st.identity) return { refused: 'Identity check must pass before anything is filed.' };
    if (n === 'filed' && !st.filed) return { refused: 'The company has not been filed yet.' };
    if (n === 'ein' && !st.ein) return { refused: 'The bank hand-off needs the EIN first.' };
    if (n === 'bank' && !st.bank) return { refused: 'Locked until the bank confirms the account is open.' };
    if (n === 'books' && !st.books) return { refused: 'Connect QuickBooks before sending invoices.' };
    if (n === 'mail' && !st.mail) return { refused: 'Connect email first.' };
    if (n === 'corp' && !st.corp) return { refused: 'A SAFE needs a C corporation.' };
  }
  const a = Number(args.amount || 0), limit = Number(st.limit || 2000);
  if (TOOLS[action] === 3) {
    if (!(a > 0)) return { refused: 'Amount must be positive.' };
    if (st.balance != null && a > Number(st.balance)) return { refused: 'Insufficient funds.' };
    if (a > limit) return { refused: 'Over the daily limit of $' + limit + ' without a passkey.' };
    if (action === 'pay' && !(st.payees || []).includes(args.payee) && a > 1500) return { refused: (args.payee || 'This payee') + ' is new: the first payment to a new payee is capped at $1,500 for 24 hours.' };
  }
  if (action === 'reply_email' && /ignore previous|account \d{4}/i.test(args.body || '')) return { refused: 'The draft repeats instructions that came from an email. Signoff does not act on instructions inside messages.' };
  if (action === 'issue_safe') { const c = Number(args.cap || 0); if (!(c >= a * 4)) return { refused: 'Cap must be at least four times the amount.' }; if (a > 5000000) return { refused: 'SAFEs over $5M go through a lawyer.' }; }
  return { tier: TOOLS[action] };
}
module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store'); res.setHeader('Access-Control-Allow-Origin', '*'); res.setHeader('Access-Control-Allow-Headers', 'Content-Type'); res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET') { const owner = (req.query && req.query.owner) || ''; if (!owner) return res.status(400).json({ error: 'owner required' }); const rec = await readOwner(owner); return res.status(200).json({ proposals: (rec.proposals || []).slice(-50).reverse() }); }
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST' });
  const b = body(req); const owner = String(b.owner || '').slice(0, 120); const agent = String(b.agent || 'unknown agent').slice(0, 80); const action = String(b.action || ''); const args = b.args && typeof b.args === 'object' ? b.args : {};
  if (!owner) return res.status(400).json({ error: 'owner required' });
  const rec = await readOwner(owner); const st = Object.assign({}, rec.state || {}, b.state || {});
  const g = gate(action, args, st);
  const id = crypto.randomBytes(8).toString('hex'); const at = new Date().toISOString();
  const decision = g.refused ? 'refused' : g.tier >= 3 ? 'code_required' : g.tier === 2 ? 'approval_required' : 'run';
  rec.proposals = (rec.proposals || []).slice(-199); rec.proposals.push({ id, at, agent, action, args, tier: g.tier ?? null, decision, reason: g.refused || null, outcome: decision === 'run' ? 'ran' : 'pending' });
  await writeOwner(owner, rec);
  return res.status(200).json({ proposal_id: id, decision, tier: g.tier ?? null, reason: g.refused || null, approve_url: decision === 'run' || decision === 'refused' ? null : SITE + '/#approve-' + id, note: decision === 'run' ? 'Allowed. Read-only or reversible; logged.' : decision === 'refused' ? 'Refused by the gate. Logged.' : 'Waiting for the owner to approve in Signoff' + (decision === 'code_required' ? ' and enter the one-time code.' : '.') });
};
