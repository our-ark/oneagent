const application = process.env.DISCORD_APPLICATION_ID;
const token = process.env.DISCORD_BOT_TOKEN;
if (!application || !token) {
  console.error('Set DISCORD_APPLICATION_ID and DISCORD_BOT_TOKEN.');
  process.exit(1);
}
const commands = [
  {
    name: 'setprefs', description: '保存你的推荐偏好',
    options: [
      { type: 3, name: 'want', description: '想看到或听到什么', required: true },
      { type: 3, name: 'avoid', description: '想避开什么', required: false }
    ]
  },
  {
    name: 'recommend', description: '生成给平台的推荐说明',
    options: [{ type: 3, name: 'platform', description: '选择平台', required: true, choices: [
      { name: 'Spotify', value: 'spotify' }, { name: '微信', value: 'wechat' }, { name: 'Amazon', value: 'amazon' }
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
