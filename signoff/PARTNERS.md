# Signoff partner setup

Every partner is a placeholder until its keys are added to the Vercel project. Nothing goes through until then.

| Partner | Env vars (Vercel, production) | Where to get them |
|---|---|---|
| Signoff AI | `ANTHROPIC_API_KEY` (optional `SIGNOFF_MODEL`) | console.anthropic.com, with a monthly spend limit |
| Partner bank (Column) | `COLUMN_API_KEY`, `COLUMN_WEBHOOK_SECRET` | dashboard.column.com → sandbox keys (test_…) |
| Formation | `FORMATION_API_KEY` | chosen filer API |
| Identity | `IDENTITY_API_KEY` | the bank's provider (Persona / Alloy) |
| QuickBooks | `QBO_CLIENT_ID`, `QBO_CLIENT_SECRET` | developer.intuit.com |
| Email | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | console.cloud.google.com |
| E-signature | `ESIGN_API_KEY` | chosen provider |
| Travel | `TRAVEL_API_KEY` | chosen provider |

Add a key (it reads the value from the prompt, nothing is stored in this folder):

    npx vercel env add COLUMN_API_KEY production

Then redeploy:

    npx vercel deploy --prod --yes

Endpoints:

- `GET /api/partner` — status of every partner.
- `POST /api/partner {partner, action, args}` — 503 until configured. Bank actions: open_account, balance, transactions, pay, issue_card (Column paths in api/partner.js, confirm against docs.column.com before go-live).
- `POST /api/webhooks` — Column webhook receiver, signature-checked with COLUMN_WEBHOOK_SECRET.
- `GET/POST /api/ai` — Signoff AI, placeholder until ANTHROPIC_API_KEY.
- `GET/POST /api/waitlist` — live (Vercel Blob).

In the app: Settings → Partners → "Live (placeholders)" sends every partner action to the server and shows each one stopping as a placeholder. "Simulated" keeps the demo flow.
