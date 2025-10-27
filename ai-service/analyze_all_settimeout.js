#!/usr/bin/env node
/**
 * Script pour trouver TOUS les setTimeout dangereux dans le frontend
 * Usage: node analyze_all_settimeout.js
 */

const fs = require('fs');
const path = require('path');

const frontendDir = path.join(__dirname, '..', 'frontend');

// Patterns dangereux
const dangerousPatterns = [
  /setTimeout\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*set[A-Z]/gs,  // setTimeout(() => { setXxx
  /setTimeout\s*\(\s*\(\s*\)\s*=>\s*{[^}]*\.[A-Z]/gs,    // setTimeout(() => { xxx.setXxx
];

// Trouver tous les fichiers .tsx et .ts
function findFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);

  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);

    if (stat.isDirectory() && !file.startsWith('.') && file !== 'node_modules') {
      findFiles(filePath, fileList);
    } else if (file.endsWith('.tsx') || file.endsWith('.ts')) {
      fileList.push(filePath);
    }
  });

  return fileList;
}

// Analyser un fichier
function analyzeFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const relativePath = path.relative(frontendDir, filePath);

  const results = [];

  // Chercher setTimeout
  const setTimeoutMatches = content.matchAll(/setTimeout/g);
  let hasSetTimeout = false;
  for (const match of setTimeoutMatches) {
    hasSetTimeout = true;
    break;
  }

  if (!hasSetTimeout) return null;

  // Chercher si le composant a isMountedRef
  const hasIsMountedRef = /isMountedRef/.test(content);

  // Trouver toutes les occurrences de setTimeout avec contexte
  const lines = content.split('\n');
  const setTimeoutLines = [];

  lines.forEach((line, index) => {
    if (line.includes('setTimeout')) {
      // Récupérer 5 lignes avant et 10 lignes après
      const contextStart = Math.max(0, index - 5);
      const contextEnd = Math.min(lines.length, index + 10);
      const context = lines.slice(contextStart, contextEnd).join('\n');

      // Vérifier si setState est appelé dans le setTimeout
      const hasSetState = /set[A-Z]/.test(context);
      const hasIsMountedCheck = /isMountedRef\.current/.test(context);

      if (hasSetState) {
        setTimeoutLines.push({
          lineNumber: index + 1,
          hasIsMountedCheck,
          context: context.substring(0, 300) // Limiter pour la lisibilité
        });
      }
    }
  });

  if (setTimeoutLines.length > 0) {
    return {
      file: relativePath,
      hasIsMountedRef,
      dangerousSetTimeouts: setTimeoutLines
    };
  }

  return null;
}

// Main
console.log('🔍 Analyse de TOUS les setTimeout dans le frontend...\n');
console.log('='.repeat(80));

const files = findFiles(frontendDir);
const results = [];

files.forEach(file => {
  const result = analyzeFile(file);
  if (result) {
    results.push(result);
  }
});

// Afficher les résultats
console.log(`\n📊 Résultats: ${results.length} fichiers avec setTimeout + setState trouvés\n`);

results.forEach((result, index) => {
  console.log(`\n${index + 1}. ⚠️  ${result.file}`);
  console.log(`   Has isMountedRef: ${result.hasIsMountedRef ? '✅' : '❌'}`);
  console.log(`   Dangerous setTimeout: ${result.dangerousSetTimeouts.length}`);

  result.dangerousSetTimeouts.forEach((timeout, i) => {
    const status = timeout.hasIsMountedCheck ? '✅ Protected' : '❌ DANGER';
    console.log(`\n   ${i + 1}) Line ${timeout.lineNumber} - ${status}`);
    console.log(`   Context:\n   ${timeout.context.split('\n').map(l => '   ' + l).join('\n')}`);
  });

  console.log('\n' + '-'.repeat(80));
});

console.log(`\n🎯 RÉSUMÉ:`);
console.log(`   Total fichiers analysés: ${files.length}`);
console.log(`   Fichiers avec setTimeout + setState: ${results.length}`);
console.log(`   Fichiers SANS protection: ${results.filter(r => !r.hasIsMountedRef || r.dangerousSetTimeouts.some(t => !t.hasIsMountedCheck)).length}`);
