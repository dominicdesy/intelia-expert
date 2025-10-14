#!/usr/bin/env node
/**
 * Script pour vérifier que toutes les clés de traduction utilisées dans le code
 * existent dans les fichiers de traduction.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Lire le fichier en.json comme référence
const enJsonPath = path.join(__dirname, 'public/locales/en.json');
const enTranslations = JSON.parse(fs.readFileSync(enJsonPath, 'utf8'));

// Extraire toutes les clés du JSON de manière récursive
function extractKeys(obj, prefix = '') {
  const keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      keys.push(...extractKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

const availableKeys = new Set(extractKeys(enTranslations));

console.log(`Total clés disponibles dans en.json: ${availableKeys.size}\n`);

// Extraire toutes les clés utilisées dans le code
try {
  const output = execSync(
    'grep -rh "t(\\"" --include="*.tsx" --include="*.ts" app/ lib/ | grep -oE "t\\(\\"[a-zA-Z0-9._]+\\"\\)" | sed "s/t(\\"//" | sed "s/\\")$//" | sort -u',
    { cwd: __dirname, encoding: 'utf8' }
  );

  const usedKeys = output.trim().split('\n').filter(k => k && k.includes('.'));

  console.log(`Total clés utilisées dans le code: ${usedKeys.length}\n`);

  // Trouver les clés manquantes
  const missingKeys = usedKeys.filter(key => !availableKeys.has(key));

  if (missingKeys.length === 0) {
    console.log('OK - Toutes les clés de traduction existent !');
  } else {
    console.log(`ERREUR - ${missingKeys.length} clés manquantes détectées:\n`);
    missingKeys.forEach(key => {
      console.log(`   - ${key}`);
    });
    process.exit(1);
  }
} catch (error) {
  console.error('Erreur lors de l\'extraction des clés:', error.message);
  process.exit(1);
}
