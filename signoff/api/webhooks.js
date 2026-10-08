// Bank webhook receiver (Column). Placeholder until COLUMN_WEBHOOK_SECRET is set.
// Column posts account and transfer events here; a verified "account open" event is what unlocks payments in the app.
const { verifyColumnWebhook } = require('./partner.js');
module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).end();
  if (!process.env.COLUMN_WEBHOOK_SECRET) return res.status(503).json({ error: 'not_configured', message: 'Webhook receiver is a placeholder until COLUMN_WEBHOOK_SECRET is set.' });
  const raw = typeof req.body === 'string' ? req.body : JSON.stringify(req.body || {});
  if (!verifyColumnWebhook(raw, req.headers['column-signature'])) return res.status(401).json({ error: 'bad signature' });
  // TODO: persist the event (Vercel Blob) and let the app poll it; the prototype simulates this with a timer.
  return res.status(200).json({ received: true });
};
