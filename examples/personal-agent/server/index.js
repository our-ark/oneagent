import express from 'express';
import { createPublicKey, verify } from 'node:crypto';
import { readFile, writeFile, rename } from 'node:fs/promises';
import { CopilotRuntime, BuiltInAgent } from '@copilotkit/runtime/v2';
import { createCopilotExpressHandler } from '@copilotkit/runtime/v2/express';

const app = express();
const dataFile = process.env.PERSONAL_AGENT_DATA || './personal-agent-discord.json';
const publicKeyHex = process.env.DISCORD_PUBLIC_KEY;
const model = process.env.COPILOT_MODEL || 'openai/gpt-4o-mini';
app.get('/api/status', (_req, res) => res.json({ copilotEnabled: Boolean(process.env.OPENAI_API_KEY) }));

// Discord must be verified against the exact raw request body before parsing.
app.post('/api/discord/interactions', express.raw({ type: 'application/json' }), async (req, res) => {
  if (!publicKeyHex || !verifyDiscord(req, publicKeyHex)) return res.status(401).send('Invalid Discord signature');
  let interaction;
  try { interaction = JSON.parse(req.body.toString('utf8')); } catch { return res.status(400).send('Invalid JSON'); }
  if (interaction.type === 1) return res.json({ type: 1 });
  if (interaction.type !== 2) return res.status(400).send('Unsupported interaction');
  const owner = interaction.member?.user?.id || interaction.user?.id;
  if (!owner) return res.status(400).send('Missing user');
  const opts = Object.fromEntries((interaction.data?.options || []).map(o => [o.name, String(o.value || '')]));
  let content;
  if (interaction.data?.name === 'setprefs') {
    const all = await loadPrefs();
    all[owner] = { want: opts.want?.slice(0, 500) || '', avoid: opts.avoid?.slice(0, 500) || '' };
    await savePrefs(all);
    content = 'Preferences saved. Use /recommend to create a recommendation brief.';
  } else if (interaction.data?.name === 'recommend') {
    const prefs = (await loadPrefs())[owner] || {};
    const platform = ({ spotify: 'Spotify podcasts', wechat: 'WeChat content', amazon: 'Amazon products' })[opts.platform];
    if (!platform) return res.json(reply('Choose spotify, wechat, or amazon.'));
    content = `Recommendation brief for ${platform}: I want ${prefs.want || 'preferences to be set with /setprefs'}; avoid ${prefs.avoid || 'nothing specified'}. Suggest candidates and explain why. This command does not change platform feeds or place orders.`;
  } else {
    content = 'Commands: /setprefs saves your preferences; /recommend creates a brief for Spotify, WeChat, or Amazon.';
  }
  return res.json(reply(content));
});

function reply(content) { return { type: 4, data: { content, flags: 64 } }; }
function verifyDiscord(req, hex) {
  try {
    const ts = req.header('x-signature-timestamp');
    const sig = req.header('x-signature-ed25519');
    if (!ts || !sig || !/^\d+$/.test(ts) || Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;
    const key = createPublicKey({ key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), Buffer.from(hex, 'hex')]), format: 'der', type: 'spki' });
    return verify(null, Buffer.concat([Buffer.from(ts), req.body]), key, Buffer.from(sig, 'hex'));
  } catch { return false; }
}
async function loadPrefs() {
  try { return JSON.parse(await readFile(dataFile, 'utf8')); } catch (error) { if (error.code === 'ENOENT') return {}; throw error; }
}
async function savePrefs(value) {
  const temp = `${dataFile}.${process.pid}.tmp`;
  await writeFile(temp, JSON.stringify(value), { mode: 0o600 });
  await rename(temp, dataFile);
}

if (process.env.OPENAI_API_KEY) {
  const runtime = new CopilotRuntime({ agents: { default: new BuiltInAgent({ model }) } });
  app.use(createCopilotExpressHandler({ runtime, basePath: '/api/copilotkit', mode: 'single-route' }));
} else {
  app.use('/api/copilotkit', (_req, res) => res.status(503).json({ error: 'Set OPENAI_API_KEY on the server to enable CopilotKit.' }));
}
app.listen(Number(process.env.PORT || 4000), '127.0.0.1');
