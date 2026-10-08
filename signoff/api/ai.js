// Signoff AI endpoint. Placeholder until ANTHROPIC_API_KEY is set in Vercel:
// GET  /api/ai  -> { configured: false|true, model }
// POST /api/ai  -> forwards { system, tools, messages } to Claude and returns the message, or 503 { error: "not_configured" }
const Anthropic = require('@anthropic-ai/sdk');
const MODEL = process.env.SIGNOFF_MODEL || 'claude-opus-5-5';
const KEY = process.env.ANTHROPIC_API_KEY || '';
function body(req){ if (!req.body) return {}; if (typeof req.body === 'string') { try { return JSON.parse(req.body); } catch (e) { return {}; } } return req.body; }
module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store'); res.setHeader('Access-Control-Allow-Origin', '*'); res.setHeader('Access-Control-Allow-Headers', 'Content-Type'); res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET') return res.status(200).json({ configured: !!KEY, model: MODEL, placeholder: !KEY });
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST' });
  if (!KEY) return res.status(503).json({ error: 'not_configured', message: 'Signoff AI is a placeholder until an API key is added to the server.' });
  const b = body(req);
  if (!Array.isArray(b.messages) || !b.messages.length || b.messages.length > 60) return res.status(400).json({ error: 'bad messages' });
  try {
    const client = new Anthropic({ apiKey: KEY });
    const msg = await client.messages.create({
      model: MODEL, max_tokens: 1024,
      system: String(b.system || '').slice(0, 8000),
      tools: Array.isArray(b.tools) ? b.tools.slice(0, 40) : undefined,
      messages: b.messages,
      output_config: { effort: 'low' }
    });
    return res.status(200).json(msg);
  } catch (e) { return res.status(502).json({ error: 'upstream', message: String(e.message || e).slice(0, 300) }); }
};
