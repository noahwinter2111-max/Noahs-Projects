// OAuth for QuickBooks Online and Gmail. GET /api/oauth?partner=books|email&owner=<id> starts; the provider calls back here with ?code&state.
// Tokens are stored in the owner's record in the private blob store, never sent to the page.
const crypto = require('crypto');
const { readOwner, writeOwner } = require('./partner.js');
const SITE = process.env.SIGNOFF_SITE || 'https://signoff-three.vercel.app';
const CB = SITE + '/api/oauth';
const P = {
  books: { env: ['QBO_CLIENT_ID', 'QBO_CLIENT_SECRET'], auth: 'https://appcenter.intuit.com/connect/oauth2', token: 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer', scope: 'com.intuit.quickbooks.accounting', id: 'QBO_CLIENT_ID', secret: 'QBO_CLIENT_SECRET' },
  email: { env: ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'], auth: 'https://accounts.google.com/o/oauth2/v2/auth', token: 'https://oauth2.googleapis.com/token', scope: 'https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly', id: 'GOOGLE_CLIENT_ID', secret: 'GOOGLE_CLIENT_SECRET' }
};
const sign = s => crypto.createHmac('sha256', process.env.OAUTH_STATE_SECRET || process.env.WAITLIST_ADMIN || 'signoff').update(s).digest('hex').slice(0, 24);
module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const q = req.query || {};
  // callback
  if (q.code && q.state) {
    const [partner, owner, sig] = String(q.state).split('|'); const p = P[partner];
    if (!p || sign(partner + '|' + owner) !== sig) return res.status(400).send('Bad state');
    if (!p.env.every(k => process.env[k])) return res.status(503).send(p.env.join(', ') + ' are not set.');
    const form = new URLSearchParams({ grant_type: 'authorization_code', code: String(q.code), redirect_uri: CB });
    const headers = { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' };
    if (partner === 'books') headers.Authorization = 'Basic ' + Buffer.from(process.env[p.id] + ':' + process.env[p.secret]).toString('base64'); else { form.set('client_id', process.env[p.id]); form.set('client_secret', process.env[p.secret]); }
    const r = await fetch(p.token, { method: 'POST', headers, body: form.toString() }); const j = await r.json();
    if (!r.ok) return res.status(502).send('Token exchange failed: ' + (j.error_description || j.error || r.status));
    const rec = await readOwner(owner);
    rec[partner] = { access_token: j.access_token, refresh_token: j.refresh_token, expires_at: Date.now() + (j.expires_in || 3600) * 1000, realm_id: q.realmId || undefined, connected_at: new Date().toISOString() };
    await writeOwner(owner, rec);
    res.setHeader('Content-Type', 'text/html'); return res.status(200).send('<!doctype html><meta charset="utf-8"><title>Connected</title><body style="font-family:system-ui;padding:40px"><h2>' + (partner === 'books' ? 'QuickBooks' : 'Gmail') + ' connected.</h2><p>Go back to Signoff and continue.</p></body>');
  }
  // start
  const partner = String(q.partner || ''); const owner = String(q.owner || 'anon'); const p = P[partner];
  if (!p) return res.status(400).send('partner=books or partner=email');
  if (!p.env.every(k => process.env[k])) { res.setHeader('Content-Type', 'text/html'); return res.status(503).send('<!doctype html><meta charset="utf-8"><body style="font-family:system-ui;padding:40px"><h2>Placeholder</h2><p>' + (partner === 'books' ? 'QuickBooks' : 'Gmail') + ' connect is a placeholder until ' + p.env.join(' and ') + ' are added to the server.</p></body>'); }
  const state = partner + '|' + owner + '|' + sign(partner + '|' + owner);
  const u = new URL(p.auth); u.searchParams.set('client_id', process.env[p.id]); u.searchParams.set('response_type', 'code'); u.searchParams.set('scope', p.scope); u.searchParams.set('redirect_uri', CB); u.searchParams.set('state', state);
  if (partner === 'email') { u.searchParams.set('access_type', 'offline'); u.searchParams.set('prompt', 'consent'); }
  res.statusCode = 302; res.setHeader('Location', u.toString()); res.end();
};
