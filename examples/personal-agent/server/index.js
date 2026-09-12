import express from 'express';
import { createPublicKey, verify } from 'node:crypto';
import { readFile, writeFile, rename } from 'node:fs/promises';
import { CopilotRuntime, BuiltInAgent } from '@copilotkit/runtime/v2';
import { createCopilotExpressHandler } from '@copilotkit/runtime/v2/express';

const app = express();
const dataFile = process.env.PERSONAL_AGENT_DATA || './personal-agent-discord.json';
const publicKeyHex = process.env.DISCORD_PUBLIC_KEY;
const model = process.env.COPILOT_MODEL || 'openai/gpt-4o-mini';

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
    content = '已保存你的偏好。使用 /recommend 获取推荐说明。';
  } else if (interaction.data?.name === 'recommend') {
    const prefs = (await loadPrefs())[owner] || {};
    const platform = ({ spotify: 'Spotify 播客', wechat: '微信内容', amazon: 'Amazon 商品' })[opts.platform];
    if (!platform) return res.json(reply('请选择 spotify、wechat 或 amazon。'));
    content = `给 ${platform} 的推荐说明：我想要 ${prefs.want || '请先用 /setprefs 设置偏好'}；避开 ${prefs.avoid || '未设置'}。请给出候选和理由。此命令不会修改平台推荐流或替你下单。`;
  } else {
    content = '可用命令：/setprefs 设置偏好；/recommend 生成 Spotify、微信或 Amazon 的推荐说明。';
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
