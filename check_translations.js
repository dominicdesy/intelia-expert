const fs = require('fs');
const data = JSON.parse(fs.readFileSync('frontend/public/locales/fr.json', 'utf8'));

const keys = [
  'error.loadVoiceSettings',
  'success.voiceSettingsSaved',
  'error.saveVoiceSettings',
  'voiceSettings.upgradeRequired',
  'voiceSettings.upgradeMessage',
  'voiceSettings.currentPlan',
  'voiceSettings.selectVoice',
  'voiceSettings.listen',
  'voiceSettings.speed',
  'voiceSettings.slower',
  'voiceSettings.normal',
  'voiceSettings.faster',
  'common.saving',
  'common.save'
];

console.log('=== VERIFICATION DES TRADUCTIONS ===\n');
keys.forEach(key => {
  const value = data[key];
  const status = value ? 'OK' : 'MANQUANT';
  console.log(`[${status}] ${key}: ${value || 'UNDEFINED'}`);
});

console.log('\n=== RECHERCHE DES OBJETS IMBRIQUES ===\n');
Object.keys(data).forEach(key => {
  if (typeof data[key] === 'object' && data[key] !== null) {
    console.log(`OBJET IMBRIQUE TROUVE: ${key}`);
    console.log(`  Cles: ${Object.keys(data[key]).join(', ')}`);
  }
});
