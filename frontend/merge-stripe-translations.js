/**
 * Script pour fusionner les traductions Stripe dans les fichiers de langues existants
 * Usage: node merge-stripe-translations.js
 */

const fs = require('fs');
const path = require('path');

const localesDir = path.join(__dirname, 'public', 'locales');

// Lire les nouvelles clés Stripe
const stripeFr = JSON.parse(fs.readFileSync(path.join(localesDir, 'stripe_keys_fr.json'), 'utf8'));
const stripeEn = JSON.parse(fs.readFileSync(path.join(localesDir, 'stripe_keys_en.json'), 'utf8'));

// Fusionner dans fr.json
const frPath = path.join(localesDir, 'fr.json');
const frData = JSON.parse(fs.readFileSync(frPath, 'utf8'));
const mergedFr = { ...frData, ...stripeFr };
fs.writeFileSync(frPath, JSON.stringify(mergedFr, null, 2), 'utf8');
console.log('✅ Clés Stripe ajoutées à fr.json');

// Fusionner dans en.json
const enPath = path.join(localesDir, 'en.json');
const enData = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const mergedEn = { ...enData, ...stripeEn };
fs.writeFileSync(enPath, JSON.stringify(mergedEn, null, 2), 'utf8');
console.log('✅ Clés Stripe ajoutées à en.json');

// Pour les autres langues, utiliser les clés anglaises par défaut
const otherLanguages = ['es', 'de', 'it', 'pt', 'nl', 'pl', 'ar', 'zh', 'ja', 'hi', 'id', 'th', 'tr', 'vi'];

otherLanguages.forEach(lang => {
  const langPath = path.join(localesDir, `${lang}.json`);
  if (fs.existsSync(langPath)) {
    const langData = JSON.parse(fs.readFileSync(langPath, 'utf8'));
    const mergedLang = { ...langData, ...stripeEn }; // Utiliser l'anglais par défaut
    fs.writeFileSync(langPath, JSON.stringify(mergedLang, null, 2), 'utf8');
    console.log(`✅ Clés Stripe ajoutées à ${lang}.json (en anglais)`);
  }
});

console.log('\n🎉 Toutes les traductions Stripe ont été fusionnées !');
console.log('📝 Note: Les langues autres que FR/EN utilisent les traductions anglaises par défaut.');
console.log('💡 Vous pouvez traduire manuellement dans les autres langues plus tard.');
