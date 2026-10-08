// Signoff partner gateway. Every call here is the REAL integration path. Nothing is faked:
// a partner without keys answers 503 not_configured and the app shows it stopping there.
//
// GET  /api/partner                        -> status of every partner and which env vars it needs
// POST /api/partner {partner, action, args, owner} -> the partner's real API, or 503 until configured
//
// Verified against vendor docs on 2026-10-07: Column auth + business entity + counterparty + webhook signing,
// Persona inquiries, Dropbox Sign signature_request/send, Duffel offer requests + orders, Gmail send/list.
// Marked CONFIRM where a path was taken from memory and should be checked in the sandbox before go-live.
const crypto = require('crypto');
const { get, put } = require('@vercel/blob');

const PARTNERS = {
  bank:      { name: 'Partner bank (Column)',   env: ['COLUMN_API_KEY', 'COLUMN_WEBHOOK_SECRET'] },
  identity:  { name: 'Identity (Persona)',      env: ['PERSONA_API_KEY', 'PERSONA_TEMPLATE_ID'] },
  formation: { name: 'Formation filer',         env: ['FORMATION_API_BASE', 'FORMATION_API_KEY'] },
  books:     { name: 'QuickBooks Online',       env: ['QBO_CLIENT_ID', 'QBO_CLIENT_SECRET'] },
  email:     { name: 'Gmail',                   env: ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'] },
  esign:     { name: 'E-signature (Dropbox Sign)', env: ['DROPBOX_SIGN_API_KEY'] },
  travel:    { name: 'Travel (Duffel)',         env: ['DUFFEL_ACCESS_TOKEN'] }
};
const configured = p => PARTNERS[p].env.every(k => !!process.env[k]);
const SITE = process.env.SIGNOFF_SITE || 'https://signoff-three.vercel.app';
function body(req){ if (!req.body) return {}; if (typeof req.body === 'string') { try { return JSON.parse(req.body); } catch (e) { return {}; } } return req.body; }
async function http(url, opts){ const r = await fetch(url, opts); const t = await r.text(); let j = {}; try { j = JSON.parse(t); } catch (e) { j = { raw: t.slice(0, 300) }; } if (!r.ok) throw new Error((j.error && (j.error.message || j.error)) || j.message || j.raw || ('HTTP ' + r.status)); return j; }

// ---- per-owner records (tokens, ids) in the private blob store. Keyed by the owner's phone hash from the app.
const ownerKey = o => 'owners/' + crypto.createHash('sha256').update(String(o || 'anon')).digest('hex').slice(0, 32) + '.json';
async function readOwner(o){ const r = await get(ownerKey(o), { access: 'private', useCache: false }); if (!r) return {}; try { return JSON.parse(await new Response(r.stream).text()) || {}; } catch (e) { return {}; } }
async function writeOwner(o, data){ await put(ownerKey(o), JSON.stringify(data), { access: 'private', addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json' }); }

// =====================================================================================
// BANK · Column. Auth: basic, empty username, API key as password (verified). Base https://api.column.com, test_/live_ keys.
const column = (path, method, data) => http('https://api.column.com' + path, { method, headers: { Authorization: 'Basic ' + Buffer.from(':' + process.env.COLUMN_API_KEY).toString('base64'), 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : undefined });
const BANK = {
  // Create the business entity from the formation result, then a checking account under it. Column runs its own KYC on the entity.
  open_account: async (a, rec) => {
    const ent = await column('/entities/business', 'POST', { business_name: a.name, ein: a.ein || undefined, ein_pending: !a.ein, legal_type: /inc/i.test(a.entity || '') ? 'corporation' : 'llc', state_of_incorporation: a.state, countries_of_operation: ['US'], account_usage: 'operating_account', description: a.desc || '' });
    const acct = await column('/bank-accounts', 'POST', { entity_id: ent.id, description: a.name + ' operating' }); // CONFIRM path in sandbox
    rec.bank = { entity_id: ent.id, account_id: acct.id }; return { entity_id: ent.id, account_id: acct.id, status: ent.verification_status || 'pending', kyc: 'bank' };
  },
  balance:      async (a, rec) => { const acct = await column('/bank-accounts/' + rec.bank.account_id, 'GET'); return { balance: (acct.balances && acct.balances.available_amount || 0) / 100, raw: acct }; },
  transactions: async (a, rec) => column('/transfers?bank_account_id=' + rec.bank.account_id + '&limit=25', 'GET'),
  // Pay: counterparty first (routing + account from the payee), then an ACH credit. Amount in cents.
  pay:          async (a, rec) => { const cp = await column('/counterparties', 'POST', { name: a.payee, routing_number: a.routing, account_number: a.account, routing_number_type: 'aba', account_type: 'checking' }); return column('/transfers/ach', 'POST', { bank_account_id: rec.bank.account_id, counterparty_id: cp.id, amount: Math.round(Number(a.amount) * 100), currency_code: 'USD', type: 'CREDIT', description: String(a.memo || '').slice(0, 10) }); }, // CONFIRM path
  schedule_payment: async (a, rec) => ({ scheduled: false, note: 'Column has no standing-order object; Signoff must run a cron that calls pay on the schedule. Not built yet.' }),
  set_aside_tax: async (a, rec) => { const sub = rec.bank.reserve_id || (await column('/bank-accounts', 'POST', { entity_id: rec.bank.entity_id, description: 'Tax reserve' })).id; rec.bank.reserve_id = sub; return column('/transfers/book', 'POST', { sender_bank_account_id: rec.bank.account_id, receiver_bank_account_id: sub, amount: Math.round(Number(a.amount) * 100), currency_code: 'USD', description: 'Tax reserve' }); }, // CONFIRM path
  issue_card:   async (a, rec) => column('/cards', 'POST', { bank_account_id: rec.bank.account_id, description: a.name, spending_limit: Math.round(Number(a.limit) * 100) }) // CONFIRM: card issuing may need a separate Column program
};
const verifyColumnWebhook = (rawBody, signature) => { const s = process.env.COLUMN_WEBHOOK_SECRET; if (!s || !signature) return false; const h = crypto.createHmac('sha256', s).update(rawBody).digest('hex'); return h.length === String(signature).length && crypto.timingSafeEqual(Buffer.from(h), Buffer.from(String(signature))); };

// =====================================================================================
// IDENTITY · Persona. POST /api/v1/inquiries, Bearer key, returns inquiry id + a one-time link the owner opens (verified).
const IDENTITY = {
  start_identity_check: async (a, rec) => { const j = await http('https://api.withpersona.com/api/v1/inquiries', { method: 'POST', headers: { Authorization: 'Bearer ' + process.env.PERSONA_API_KEY, 'Content-Type': 'application/json', 'Persona-Version': '2025-12-08' }, body: JSON.stringify({ data: { attributes: { 'inquiry-template-id': process.env.PERSONA_TEMPLATE_ID, 'redirect-uri': SITE, fields: { 'name-first': a.first || '', 'name-last': a.last || '', 'phone-number': a.phone || '' } } }, meta: { 'auto-create-one-time-link': true } }) }); rec.identity = { inquiry_id: j.data.id, status: 'pending' }; return { inquiry_id: j.data.id, link: j.meta && j.meta['one-time-link'], status: 'pending' }; },
  status: async (a, rec) => { const j = await http('https://api.withpersona.com/api/v1/inquiries/' + rec.identity.inquiry_id, { headers: { Authorization: 'Bearer ' + process.env.PERSONA_API_KEY, 'Persona-Version': '2025-12-08' } }); return { status: j.data.attributes.status }; }
};

// =====================================================================================
// FORMATION · there is no universal filing API. This is Signoff's contract with whichever filer signs:
// POST {base}/filings {entity, name, state, owner} -> {id, status}; GET {base}/filings/{id}; POST {base}/filings/{id}/ein. Bearer key.
const filer = (path, method, data) => http(process.env.FORMATION_API_BASE.replace(/\/$/, '') + path, { method, headers: { Authorization: 'Bearer ' + process.env.FORMATION_API_KEY, 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : undefined });
const FORMATION = {
  file_formation: async (a, rec) => { const j = await filer('/filings', 'POST', { entity: a.entity, name: a.name, state: a.state, owner: a.owner, registered_agent: true, operating_agreement: true }); rec.formation = { filing_id: j.id }; return j; },
  status:         async (a, rec) => filer('/filings/' + rec.formation.filing_id, 'GET'),
  apply_ein:      async (a, rec) => { const j = await filer('/filings/' + rec.formation.filing_id + '/ein', 'POST', {}); if (j.ein) rec.formation.ein = j.ein; return j; },
  convert_to_corp: async (a, rec) => filer('/filings', 'POST', { entity: 'Inc.', name: a.name, state: 'Delaware', foreign_qualification: a.home_state, convert_from: rec.formation && rec.formation.filing_id, shares: 10000000 })
};

// =====================================================================================
// BOOKS · QuickBooks Online. OAuth2 via /api/oauth?partner=books. Tokens live in the owner record. CONFIRM minorversion in sandbox.
async function qboToken(rec){ const t = rec.books; if (!t) throw new Error('QuickBooks is not connected for this owner. Open the connect link first.'); if (Date.now() < t.expires_at - 60000) return t; const j = await http('https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer', { method: 'POST', headers: { Authorization: 'Basic ' + Buffer.from(process.env.QBO_CLIENT_ID + ':' + process.env.QBO_CLIENT_SECRET).toString('base64'), 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' }, body: 'grant_type=refresh_token&refresh_token=' + encodeURIComponent(t.refresh_token) }); Object.assign(t, { access_token: j.access_token, refresh_token: j.refresh_token || t.refresh_token, expires_at: Date.now() + (j.expires_in || 3600) * 1000 }); return t; }
const qboBase = () => process.env.QBO_ENV === 'production' ? 'https://quickbooks.api.intuit.com' : 'https://sandbox-quickbooks.api.intuit.com';
async function qbo(rec, path, method, data){ const t = await qboToken(rec); return http(qboBase() + '/v3/company/' + t.realm_id + path + (path.includes('?') ? '&' : '?') + 'minorversion=73', { method, headers: { Authorization: 'Bearer ' + t.access_token, 'Content-Type': 'application/json', Accept: 'application/json' }, body: data ? JSON.stringify(data) : undefined }); }
const BOOKS = {
  connect_books: async (a, rec) => ({ connect_url: SITE + '/api/oauth?partner=books&owner=' + encodeURIComponent(a.owner || ''), connected: !!rec.books }),
  send_invoice:  async (a, rec) => { const cust = await qbo(rec, '/customer', 'POST', { DisplayName: a.to }).catch(async () => { const q = await qbo(rec, "/query?query=" + encodeURIComponent("select * from Customer where DisplayName = '" + String(a.to).replace(/'/g, "\\'") + "'"), 'GET'); return { Customer: q.QueryResponse.Customer[0] }; }); const inv = await qbo(rec, '/invoice', 'POST', { CustomerRef: { value: cust.Customer.Id }, Line: [{ Amount: Number(a.amount), DetailType: 'SalesItemLineDetail', Description: a.memo || '', SalesItemLineDetail: { ItemRef: { value: '1' } } }], SalesTermRef: a.terms ? undefined : undefined }); return { invoice_id: inv.Invoice.Id, doc_number: inv.Invoice.DocNumber }; },
  pl_report:     async (a, rec) => qbo(rec, '/reports/ProfitAndLoss?date_macro=This%20Fiscal%20Year-to-date', 'GET')
};

// =====================================================================================
// EMAIL · Gmail. OAuth2 via /api/oauth?partner=email. messages.send with base64url MIME; messages.list with q (verified).
async function gToken(rec){ const t = rec.email; if (!t) throw new Error('Gmail is not connected for this owner. Open the connect link first.'); if (Date.now() < t.expires_at - 60000) return t; const j = await http('https://oauth2.googleapis.com/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_id: process.env.GOOGLE_CLIENT_ID, client_secret: process.env.GOOGLE_CLIENT_SECRET, refresh_token: t.refresh_token, grant_type: 'refresh_token' }).toString() }); Object.assign(t, { access_token: j.access_token, expires_at: Date.now() + (j.expires_in || 3600) * 1000 }); return t; }
const b64url = s => Buffer.from(s).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
async function gmailSend(rec, to, subject, text){ const t = await gToken(rec); const raw = b64url(['To: ' + to, 'Subject: ' + subject, 'Content-Type: text/plain; charset=utf-8', '', text].join('\r\n')); return http('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', { method: 'POST', headers: { Authorization: 'Bearer ' + t.access_token, 'Content-Type': 'application/json' }, body: JSON.stringify({ raw }) }); }
const EMAIL = {
  connect_email: async (a, rec) => ({ connect_url: SITE + '/api/oauth?partner=email&owner=' + encodeURIComponent(a.owner || ''), connected: !!rec.email }),
  list_inbox:    async (a, rec) => { const t = await gToken(rec); const l = await http('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=10&q=' + encodeURIComponent(a.q || 'newer_than:30d'), { headers: { Authorization: 'Bearer ' + t.access_token } }); const out = []; for (const m of (l.messages || []).slice(0, 10)) { const d = await http('https://gmail.googleapis.com/gmail/v1/users/me/messages/' + m.id + '?format=metadata&metadataHeaders=From&metadataHeaders=Subject', { headers: { Authorization: 'Bearer ' + t.access_token } }); const h = n => (d.payload.headers.find(x => x.name === n) || {}).value || ''; out.push({ id: m.id, from: h('From'), subj: h('Subject'), preview: d.snippet || '' }); } return { inbox: out }; },
  reply_email:   async (a, rec) => gmailSend(rec, a.to, a.subject, a.body),
  send_investor_update: async (a, rec) => { const r = []; for (const to of (a.recipients || [])) r.push(await gmailSend(rec, to, a.title, a.body || '')); return { sent: r.length }; }
};

// =====================================================================================
// E-SIGN · Dropbox Sign. POST /v3/signature_request/send, basic auth with the API key, signers + file_urls (verified).
const dsign = data => http('https://api.hellosign.com/v3/signature_request/send', { method: 'POST', headers: { Authorization: 'Basic ' + Buffer.from(process.env.DROPBOX_SIGN_API_KEY + ':').toString('base64'), 'Content-Type': 'application/json' }, body: JSON.stringify(Object.assign({ test_mode: process.env.DROPBOX_SIGN_LIVE === '1' ? false : true }, data)) });
const ESIGN = {
  send_contract: async (a, rec) => dsign({ title: 'Services agreement · ' + a.to, subject: 'Services agreement from ' + (a.company || 'Signoff'), message: 'Scope: ' + a.scope + '. Fee: $' + a.fee + '. Net 30. Either side may end with 14 days notice.', signers: [{ name: a.to, email_address: a.to_email || '', order: 0 }, { name: a.owner_name || 'Owner', email_address: a.owner_email || '', order: 1 }], file_urls: [a.file_url || SITE + '/docs/services-agreement.pdf'] }),
  issue_safe:    async (a, rec) => dsign({ title: 'Post-money SAFE · ' + a.name, subject: 'SAFE from ' + (a.company || 'the company'), message: 'Investment $' + a.amount + ', valuation cap $' + a.cap + (a.discount ? ', discount ' + a.discount + '%' : '') + '. YC post-money SAFE, no side letter.', signers: [{ name: a.name, email_address: a.email || '', order: 0 }, { name: a.owner_name || 'Founder', email_address: a.owner_email || '', order: 1 }], file_urls: [a.file_url || SITE + '/docs/safe-postmoney.pdf'] })
};

// =====================================================================================
// TRAVEL · Duffel. Offer request, pick the cheapest offer, create the order on the company card (verified endpoints; Duffel-Version v2).
const duffel = (path, data) => http('https://api.duffel.com' + path, { method: data ? 'POST' : 'GET', headers: { Authorization: 'Bearer ' + process.env.DUFFEL_ACCESS_TOKEN, 'Duffel-Version': 'v2', 'Content-Type': 'application/json', Accept: 'application/json' }, body: data ? JSON.stringify({ data }) : undefined });
const TRAVEL = {
  book_travel: async (a, rec) => { const req = await duffel('/air/offer_requests?return_offers=true', { slices: [{ origin: a.from || 'AUS', destination: a.to_iata || a.to, departure_date: a.depart }, { origin: a.to_iata || a.to, destination: a.from || 'AUS', departure_date: a.return }], passengers: [{ type: 'adult', given_name: a.first || 'Owner', family_name: a.last || 'Signoff' }], cabin_class: 'economy' }); const offers = (req.data.offers || []).sort((x, y) => Number(x.total_amount) - Number(y.total_amount)); if (!offers.length) throw new Error('No offers'); const off = offers[0]; const pid = req.data.passengers[0].id; const order = await duffel('/air/orders', { selected_offers: [off.id], passengers: [{ id: pid, given_name: a.first || 'Owner', family_name: a.last || 'Signoff', born_on: a.born_on || '1990-01-01', email: a.email || '', phone_number: a.phone || '', gender: a.gender || 'm', title: a.title || 'mr' }], payments: [{ type: 'balance', currency: off.total_currency, amount: off.total_amount }] }); return { order_id: order.data.id, amount: Number(off.total_amount), currency: off.total_currency, booking_reference: order.data.booking_reference }; }
};

const IMPL = { bank: BANK, identity: IDENTITY, formation: FORMATION, books: BOOKS, email: EMAIL, esign: ESIGN, travel: TRAVEL };

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store'); res.setHeader('Access-Control-Allow-Origin', '*'); res.setHeader('Access-Control-Allow-Headers', 'Content-Type'); res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET') { const out = {}; for (const p in PARTNERS) out[p] = { name: PARTNERS[p].name, configured: configured(p), placeholder: !configured(p), needs: PARTNERS[p].env, actions: Object.keys(IMPL[p]) }; return res.status(200).json({ partners: out, ai: { configured: !!process.env.ANTHROPIC_API_KEY, needs: ['ANTHROPIC_API_KEY'] } }); }
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST' });
  const { partner, action, args, owner } = body(req);
  if (!PARTNERS[partner]) return res.status(400).json({ error: 'unknown partner' });
  if (!configured(partner)) return res.status(503).json({ error: 'not_configured', partner, name: PARTNERS[partner].name, needs: PARTNERS[partner].env, message: PARTNERS[partner].name + ' is a placeholder until its keys are added to the server. The call you made would have run its real API.' });
  const fn = IMPL[partner][action]; if (!fn) return res.status(400).json({ error: 'unknown action', actions: Object.keys(IMPL[partner]) });
  try { const rec = await readOwner(owner); const out = await fn(Object.assign({ owner }, args || {}), rec); await writeOwner(owner, rec); return res.status(200).json(out); }
  catch (e) { return res.status(502).json({ error: 'upstream', partner, message: String(e.message || e).slice(0, 300) }); }
};
module.exports.verifyColumnWebhook = verifyColumnWebhook;
module.exports.readOwner = readOwner; module.exports.writeOwner = writeOwner;
