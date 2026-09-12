const application = process.env.DISCORD_APPLICATION_ID;
const token = process.env.DISCORD_BOT_TOKEN;
if (!application || !token) {
  console.error('Set DISCORD_APPLICATION_ID and DISCORD_BOT_TOKEN.');
  process.exit(1);
}
const commands = [
  {
    name: 'setprefs', description: 'Save your recommendation preferences',
    options: [
      { type: 3, name: 'want', description: 'What you want to see or hear', required: true },
      { type: 3, name: 'avoid', description: 'What you want to avoid', required: false }
    ]
  },
  {
    name: 'recommend', description: 'Create a recommendation brief for a platform',
    options: [{ type: 3, name: 'platform', description: 'Choose a platform', required: true, choices: [
      { name: 'Spotify', value: 'spotify' }, { name: 'WeChat', value: 'wechat' }, { name: 'Amazon', value: 'amazon' }
    ] }]
  }
];
const response = await fetch(`https://discord.com/api/v10/applications/${encodeURIComponent(application)}/commands`, {
  method: 'PUT',
  headers: { Authorization: `Bot ${token}`, 'Content-Type': 'application/json' },
  body: JSON.stringify(commands)
});
if (!response.ok) {
  console.error(`Discord command registration failed: ${response.status} ${await response.text()}`);
  process.exit(1);
}
console.log('Registered /setprefs and /recommend.');
