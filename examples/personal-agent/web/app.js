const scenarios = [
  { name: 'Research and information', short: 'Find what deserves your attention', detail: 'Add a topic, sources, or candidate links. Compare relevance, credibility, and value.', output: 'A ranked reading list with reasons' },
  { name: 'Scheduling and communication', short: 'Plan your time and prepare replies', detail: 'Add invitations, timing, and people. Compare them with your priorities and draft a response.', output: 'Suggested times, talking points, and a draft to review' },
  { name: 'Shopping and services', short: 'Compare choices against your budget', detail: 'Compare price, delivery, service, and risk. Purchases always need your approval.', output: 'A shortlist and pre-purchase review' },
  { name: 'Cross-agent coordination', short: 'Bring specialist agents together', detail: 'Assign specialist tasks, check for conflicts, and combine their findings.', output: 'Task split, evidence check, and recommendation' },
  { name: 'Ongoing personal tasks', short: 'Keep up with recurring decisions', detail: 'Track subscriptions, travel, reimbursements, or other recurring work. Review exceptions.', output: 'A recurring record and approval queue' }
];
const key = 'dreamphones-personal-agent-v1';
const defaults = {
  profile: { name: '', focus: '', goals: '', preferences: '', avoid: '' },
  policy: { auto: 'Read public information, summarize, and compare', approve: 'Send messages, register, book, pay, or share private data', never: 'Sign contracts, transfer funds, or delete accounts' },
  decisions: [], platforms: { spotify: { want: '', avoid: '' }, wechat: { want: '', avoid: '' }, amazon: { want: '', avoid: '' } }, chat: [], checkouts: []
};
let data;
try { data = { ...structuredClone(defaults), ...JSON.parse(localStorage.getItem(key) || '{}') }; }
catch { data = structuredClone(defaults); }
data.profile = { ...defaults.profile, ...data.profile };
data.policy = { ...defaults.policy, ...data.policy };
data.platforms = { ...defaults.platforms, ...data.platforms };
data.decisions = Array.isArray(data.decisions) ? data.decisions : [];
data.chat = Array.isArray(data.chat) ? data.chat : [];
data.checkouts = Array.isArray(data.checkouts) ? data.checkouts : [];
const $ = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
function save() { localStorage.setItem(key, JSON.stringify(data)); window.dispatchEvent(new Event('personal-agent:changed')); }
function toast(message) { $('toast').textContent = message; $('toast').classList.add('show'); clearTimeout(window.toastTimer); window.toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2500); }
function values(form) { return Object.fromEntries(new FormData(form).entries()); }
function fill(form, object) { for (const [field, value] of Object.entries(object)) if (form.elements[field]) form.elements[field].value = value; }

const titles = { today: 'Make better decisions, your way', bot: 'Recommendations that know you', profile: 'Help your agent know you', policy: 'Set your action boundaries', design: 'Five scenarios, one decision flow' };
function show(view) {
  document.querySelectorAll('.nav,.view').forEach(element => element.classList.toggle('active', element.dataset.view === view || element.id === view));
  $('pageTitle').textContent = titles[view];
}
document.querySelectorAll('.nav').forEach(button => button.onclick = () => show(button.dataset.view));
$('dateLabel').textContent = new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', weekday: 'long' }).format(new Date());
$('scenarioGrid').innerHTML = scenarios.map((s, i) => `<button class="scenario-card" data-index="${i}"><span class="number">0${i + 1}</span><h3>${s.name}</h3><p>${s.short}</p></button>`).join('');
$('scenario').innerHTML = scenarios.map((s, i) => `<option value="${i}">${s.name}</option>`).join('');
$('docsGrid').innerHTML = scenarios.map((s, i) => `<article class="panel doccard"><span class="number">0${i + 1} / SCENARIO</span><h3>${s.name}</h3><p><b>Input:</b> ${s.detail}</p><p><b>Output:</b> ${s.output}</p></article>`).join('');
document.querySelectorAll('.scenario-card').forEach(card => card.onclick = () => { $('scenario').value = card.dataset.index; document.querySelectorAll('.scenario-card').forEach(other => other.classList.toggle('selected', other === card)); $('goal').focus(); });
fill($('profileForm'), data.profile);
fill($('policyForm'), data.policy);
$('profileForm').onsubmit = event => { event.preventDefault(); data.profile = values(event.target); save(); $('profileSaved').textContent = 'Saved'; toast('Profile saved'); };
$('policyForm').onsubmit = event => { event.preventDefault(); data.policy = values(event.target); save(); $('policySaved').textContent = 'Saved'; toast('Action policy saved'); };

function words(value) { return String(value || '').toLowerCase().split(/[\s,.;:\n]+/).filter(word => word.length > 1); }
function recommend(options, criteria, profile) {
  if (!options.length) return 'Collect at least two options, then compare them against your priorities.';
  const wanted = words([criteria, profile.focus, profile.goals, profile.preferences].join(' '));
  const avoided = words(profile.avoid);
  const ranked = options.map((option, index) => ({ option, index, score: wanted.filter(word => option.toLowerCase().includes(word)).length - avoided.filter(word => option.toLowerCase().includes(word)).length * 2 })).sort((a, b) => b.score - a.score || a.index - b.index);
  if (ranked[0].score <= 0) return `There is not enough information to rank these reliably. Check whether “${ranked[0].option}” meets ${criteria || 'your goal'} and add price, benefits, and risks.`;
  return `“${ranked[0].option}” matches ${ranked[0].score} of your stated preferences or criteria. Verify price, risks, and sources before acting.`;
}
$('decisionForm').onsubmit = event => {
  event.preventDefault();
  const options = $('options').value.split('\n').map(s => s.trim()).filter(Boolean);
  const goal = $('goal').value.trim(); if (!goal) return;
  data.decisions.unshift({ id: crypto.randomUUID(), scenario: Number($('scenario').value), goal, criteria: $('criteria').value.trim(), limit: $('limit').value.trim(), options, recommendation: recommend(options, $('criteria').value.trim(), data.profile), status: 'pending', created: new Date().toISOString() });
  save(); event.target.reset(); renderDecisions(); toast('Decision card added for review');
};
function renderDecisions() {
  $('taskCount').textContent = data.decisions.length;
  $('pendingCount').textContent = data.decisions.filter(d => d.status === 'pending').length;
  const list = $('decisionList');
  list.innerHTML = data.decisions.length ? data.decisions.map(d => `<article class="decision-card"><div class="meta"><span>${escapeHtml(scenarios[d.scenario]?.name || 'Other')}</span><span>${new Date(d.created).toLocaleDateString('en-US')}</span></div><h3>${escapeHtml(d.goal)}</h3>${d.criteria ? `<p>Criterion: ${escapeHtml(d.criteria)}</p>` : ''}${d.limit ? `<p>Limit: ${escapeHtml(d.limit)}</p>` : ''}${d.options?.length ? `<p>Options: ${escapeHtml(d.options.join(' · '))}</p>` : ''}<p class="recommend">${escapeHtml(d.recommendation)}</p><div class="actions">${d.status === 'pending' ? `<button class="approve" data-action="approve" data-id="${d.id}">Accept suggestion</button><button data-action="reject" data-id="${d.id}">Not now</button>` : `<span class="status">${d.status === 'approved' ? 'Accepted' : 'Not accepted'}</span>`}<button data-action="delete" data-id="${d.id}">Delete</button></div></article>`).join('') : '<div class="empty"><strong>No decision cards yet</strong>Choose a scenario and describe a decision you want help with.</div>';
  list.querySelectorAll('button[data-action]').forEach(button => button.onclick = () => { const index = data.decisions.findIndex(d => d.id === button.dataset.id); if (index < 0) return; if (button.dataset.action === 'delete') data.decisions.splice(index, 1); else data.decisions[index].status = button.dataset.action === 'approve' ? 'approved' : 'rejected'; save(); renderDecisions(); toast('Decision updated'); });
}
renderDecisions();
$('exportBtn').onclick = () => { const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = 'personal-agent-data.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast('Data exported'); };

const names = { spotify: 'Spotify podcasts', wechat: 'WeChat content', amazon: 'Amazon products' };
const platform = $('platformSelect');
function brief() { const p = data.platforms[platform.value]; return `Recommendation brief for ${names[platform.value]}:\nI want: ${p.want || data.profile.preferences || 'Please set my preferences first'}\nAvoid: ${p.avoid || data.profile.avoid || 'Not specified'}\nMy current focus: ${data.profile.focus || 'Not specified'}. Prioritize matching options and explain why.`; }
function renderPlatform() { const p = data.platforms[platform.value]; $('platformWant').value = p.want; $('platformAvoid').value = p.avoid; $('platformBrief').textContent = brief(); $('searchPlatform').textContent = platform.value === 'wechat' ? 'Copy WeChat search term' : 'Search platform'; }
platform.onchange = renderPlatform;
$('savePlatform').onclick = () => { data.platforms[platform.value] = { want: $('platformWant').value.trim(), avoid: $('platformAvoid').value.trim() }; save(); renderPlatform(); toast('Platform preferences saved'); };
async function copy(text, success) { try { await navigator.clipboard.writeText(text); toast(success); } catch { toast('Please copy the text manually'); } }
$('copyBrief').onclick = () => copy(brief(), 'Brief copied');
$('searchPlatform').onclick = () => { const query = (data.platforms[platform.value].want || data.profile.focus || 'recommendations').trim(); if (platform.value === 'wechat') return copy(query, 'Search term copied for WeChat'); const url = platform.value === 'spotify' ? `https://open.spotify.com/search/${encodeURIComponent(query)}/shows` : `https://www.amazon.com/s?k=${encodeURIComponent(query)}`; window.open(url, '_blank', 'noopener,noreferrer'); };
function share(base) { window.open(base + encodeURIComponent(brief()), '_blank', 'noopener,noreferrer'); }
$('shareTelegram').onclick = () => share('https://t.me/share/url?text=');
$('shareWhatsapp').onclick = () => share('https://wa.me/?text=');
$('shareDiscord').onclick = () => copy(brief(), 'Brief copied for Discord');
renderPlatform();

function botAnswer(message) {
  const m = message.toLowerCase();
  const selected = /podcast|spotify|listen|audio/.test(m) ? 'spotify' : /wechat|article|video|read|content/.test(m) ? 'wechat' : /amazon|shop|buy|product|purchase/.test(m) ? 'amazon' : platform.value;
  platform.value = selected; renderPlatform();
  const p = data.platforms[selected], wish = p.want || data.profile.preferences || data.profile.focus, avoid = p.avoid || data.profile.avoid;
  if (selected === 'spotify') return `I can filter podcast ideas for “${wish || 'your preferred topics'}” and avoid “${avoid || 'content you dislike'}”. Save more specific preferences on the right and open Spotify search. I have not read your listening history, so I will not invent shows.`;
  if (selected === 'wechat') return `I can prioritize content related to “${data.profile.focus || 'your goals'}” and avoid “${avoid || 'content you dislike'}”. Copy the brief or search term on the right. I cannot directly change your WeChat feed.`;
  return `I can compare products against “${wish || 'your needs'}” and avoid “${avoid || 'poor matches'}”. Search for products, then add the item, seller, and price below to create a pre-purchase review card.`;
}
function renderChat() { const log = $('chatLog'); log.innerHTML = data.chat.length ? data.chat.map(m => `<div class="bubble ${m.role === 'user' ? 'user' : 'assistant'}">${escapeHtml(m.text)}</div>`).join('') : '<div class="bubble assistant">Hi, I am your recommendation bot. Tell me what podcasts, WeChat content, or products you want. I will use your profile to shape a recommendation brief.</div>'; log.scrollTop = log.scrollHeight; }
$('chatForm').onsubmit = event => { event.preventDefault(); const input = $('chatInput'), message = input.value.trim(); if (!message) return; data.chat.push({ role: 'user', text: message }, { role: 'assistant', text: botAnswer(message) }); save(); renderChat(); input.value = ''; };
document.querySelectorAll('[data-prompt]').forEach(button => button.onclick = () => { $('chatInput').value = button.dataset.prompt; $('chatForm').requestSubmit(); });
renderChat();

function safeUrl(raw) { try { const url = new URL(raw); return /^https?:$/.test(url.protocol) ? url.href : ''; } catch { return ''; } }
function renderCheckouts() {
  const list = $('checkoutList');
  list.innerHTML = data.checkouts.map(c => `<article class="checkout-card"><div class="checkout-summary"><div><strong>${escapeHtml(c.item)}</strong><p>${escapeHtml(c.seller)} · ${escapeHtml(c.price)}</p><p>${escapeHtml(c.reason || 'No reason added yet')}</p></div><span class="status">${c.status === 'approved' ? 'Approved to view' : 'Needs review'}</span></div><div class="checkout-actions">${c.status === 'pending' ? `<button class="primary" data-action="approve" data-id="${c.id}">Approve and view product</button>` : ''}<button class="quiet" data-action="delete" data-id="${c.id}">Delete</button></div><p class="fineprint">Approval records your intent only. Confirm payment on the merchant site.</p></article>`).join('');
  list.querySelectorAll('button[data-action]').forEach(button => button.onclick = () => { const index = data.checkouts.findIndex(c => c.id === button.dataset.id); if (index < 0) return; const card = data.checkouts[index]; if (button.dataset.action === 'delete') data.checkouts.splice(index, 1); else { card.status = 'approved'; if (card.url) window.open(card.url, '_blank', 'noopener,noreferrer'); } save(); renderCheckouts(); toast(button.dataset.action === 'delete' ? 'Review card deleted' : 'Approval recorded; check details and pay on the merchant site'); });
}
$('checkoutForm').onsubmit = event => { event.preventDefault(); const v = values(event.target), url = v.url ? safeUrl(v.url) : ''; if (v.url && !url) return toast('Enter a valid product URL'); data.checkouts.unshift({ id: crypto.randomUUID(), item: v.item.trim(), price: v.price.trim(), seller: v.seller.trim(), url, reason: v.reason.trim(), status: 'pending' }); save(); renderCheckouts(); event.target.reset(); toast('Purchase review card created'); };
renderCheckouts();

if (document.modelContext?.registerTool) {
  try { Promise.resolve(document.modelContext.registerTool({
    name: 'stage_personal_decision', title: 'Create a personal decision card', description: 'Create a decision card for the user to review. Does not execute external actions.',
    inputSchema: { type: 'object', properties: { scenario: { type: 'integer', minimum: 0, maximum: 4 }, goal: { type: 'string', minLength: 1 }, criteria: { type: 'string' }, options: { type: 'array', items: { type: 'string' } } }, required: ['scenario', 'goal'], additionalProperties: false },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    execute(input) { if (!input || !Number.isInteger(input.scenario) || input.scenario < 0 || input.scenario > 4 || typeof input.goal !== 'string' || !input.goal.trim() || (input.options !== undefined && (!Array.isArray(input.options) || input.options.some(x => typeof x !== 'string')))) throw new Error('Invalid decision input'); const decision = { id: crypto.randomUUID(), scenario: input.scenario, goal: input.goal.trim(), criteria: input.criteria || '', limit: '', options: input.options || [], recommendation: recommend(input.options || [], input.criteria || '', data.profile), status: 'pending', created: new Date().toISOString() }; data.decisions.unshift(decision); save(); renderDecisions(); show('today'); return { id: decision.id, status: 'pending' }; }
  })).catch(() => {}); } catch { /* Browser Model Context is optional. */ }
}
