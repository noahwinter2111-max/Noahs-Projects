// Bank webhook receiver (Column). Column signs the raw JSON body with HMAC-SHA256 using the endpoint's signing secret,
// sent in the Column-Signature header (verified in docs). Placeholder until COLUMN_WEBHOOK_SECRET is set.
// A verified event is appended to the owner's record; the app polls /api/partner bank.status to see "account open".
const { verifyColumnWebhook, readOwner, writeOwner } = require('./partner.js');
module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).end();
  if (!process.env.COLUMN_WEBHOOK_SECRET) return res.status(503).json({ error: 'not_configured', message: 'Webhook receiver is a placeholder until COLUMN_WEBHOOK_SECRET is set.' });
  const raw = typeof req.body === 'string' ? req.body : JSON.stringify(req.body || {});
  if (!verifyColumnWebhook(raw, req.headers['column-signature'])) return res.status(401).json({ error: 'bad signature' });
  let ev = {}; try { ev = JSON.parse(raw); } catch (e) {}
  const owner = (ev.data && ev.data.metadata && ev.data.metadata.owner) || 'unrouted';
  const rec = await readOwner(owner); rec.events = (rec.events || []).slice(-50); rec.events.push({ type: ev.type, id: ev.id, at: new Date().toISOString() });
  if (/entity\.verified|bank_account\.(created|verified)/.test(ev.type || '')) rec.bank = Object.assign(rec.bank || {}, { status: 'open' });
  await writeOwner(owner, rec);
  return res.status(200).json({ received: true });
};
