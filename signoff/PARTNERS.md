# Signoff partner setup

Every feature in the app takes the real API path by default. A partner without keys stops at the server and says so. Nothing is faked unless you switch Settings → Partners → "Simulated walkthrough".

| Partner | Env vars (Vercel, production) | Where to get them | Status of the code |
|---|---|---|---|
| Signoff AI | `ANTHROPIC_API_KEY` (optional `SIGNOFF_MODEL`) | console.anthropic.com, set a monthly spend limit | Done |
| Bank · Column | `COLUMN_API_KEY`, `COLUMN_WEBHOOK_SECRET` | dashboard.column.com (test_ keys are instant) | Auth, entity, counterparty, webhook signing verified against docs. Bank-account, ACH, book-transfer and card paths marked CONFIRM in api/partner.js: check in the sandbox. |
| Identity · Persona | `PERSONA_API_KEY`, `PERSONA_TEMPLATE_ID` | withpersona.com dashboard | Verified. Creates an inquiry and returns the one-time link the owner opens. |
| Formation filer | `FORMATION_API_BASE`, `FORMATION_API_KEY` | whichever filer signs | No universal API exists. api/partner.js states the contract Signoff expects (filings, ein, convert). |
| QuickBooks Online | `QBO_CLIENT_ID`, `QBO_CLIENT_SECRET`, optional `QBO_ENV=production` | developer.intuit.com, redirect URI `https://signoff-three.vercel.app/api/oauth` | OAuth, refresh, invoice, P&L report. Sandbox by default. |
| Gmail | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | console.cloud.google.com, redirect URI `https://signoff-three.vercel.app/api/oauth` | OAuth, refresh, list inbox, send (verified endpoints). Needs Google's OAuth app review before strangers can connect. |
| E-signature · Dropbox Sign | `DROPBOX_SIGN_API_KEY`, optional `DROPBOX_SIGN_LIVE=1` | hellosign.com developers | Verified. Test mode by default. Needs the agreement and SAFE PDFs at /docs/. |
| Travel · Duffel | `DUFFEL_ACCESS_TOKEN` | duffel.com | Verified. Cheapest offer, order paid from the Duffel balance. |
| OAuth state | `OAUTH_STATE_SECRET` | any long random string | Optional; falls back to the waitlist admin key. |

Add a key (the value is read from the prompt, nothing is stored in this folder):

    npx vercel env add COLUMN_API_KEY production

Then redeploy:

    npx vercel deploy --prod --yes

## Endpoints

- `GET /api/partner` — status and available actions for every partner.
- `POST /api/partner {partner, action, args, owner}` — the real call. 503 `not_configured` until that partner's keys exist. Per-owner records (bank ids, OAuth tokens) live in the private blob store, keyed by a hash of the owner's phone.
- `GET /api/oauth?partner=books|email&owner=…` — starts the OAuth flow; the provider calls back to the same URL.
- `POST /api/webhooks` — Column webhook receiver. Verifies `Column-Signature` (HMAC-SHA256 of the raw body), records the event, marks the account open on entity/account verification events.
- `GET/POST /api/ai` — Signoff AI. 503 until `ANTHROPIC_API_KEY`.
- `GET/POST /api/waitlist` — live.

## What still needs a decision before go-live

- Which formation filer, and whether its API matches the contract in api/partner.js.
- Standing payments: Column has no standing-order object, so Signoff needs a scheduled job that calls `pay` on the schedule.
- Routing and account numbers for payees: the app does not collect them yet; the agent will have to ask before `pay` can run for real.
- Column webhook events need the owner id in metadata so they route to the right record.
