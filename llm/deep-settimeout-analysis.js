#!/usr/bin/env node
/**
 * Analyse approfondie des setTimeout avec suivi des appels de fonction
 * Détecte les protections isMountedRef MÊME dans les fonctions appelées
 *
 * Usage: node deep-settimeout-analysis.js
 */

const fs = require('fs');
const path = require('path');

const frontendDir = path.join(__dirname, '..', 'frontend');

// Carte globale des fonctions et leurs protections
const functionProtections = new Map();

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

// Analyser un fichier pour trouver les fonctions et leurs protections
function extractFunctions(content, filePath) {
  const functions = [];

  // Pattern pour détecter les fonctions
  const functionPatterns = [
    // const functionName = useCallback(() => { ... }, []);
    /const\s+(\w+)\s*=\s*useCallback\s*\(\s*(?:async\s*)?\(\s*[^)]*\)\s*=>\s*\{([\s\S]*?)\}\s*,\s*\[/g,
    // const functionName = useCallback(async () => { ... }, []);
    /const\s+(\w+)\s*=\s*useCallback\s*\(\s*async\s*\(\s*[^)]*\)\s*=>\s*\{([\s\S]*?)\}\s*,\s*\[/g,
    // const functionName = async () => { ... }
    /const\s+(\w+)\s*=\s*async\s*\(\s*[^)]*\)\s*=>\s*\{([\s\S]*?)\n\s*\}/g,
    // const functionName = () => { ... }
    /const\s+(\w+)\s*=\s*\(\s*[^)]*\)\s*=>\s*\{([\s\S]*?)\n\s*\}/g,
    // function functionName() { ... }
    /function\s+(\w+)\s*\(\s*[^)]*\)\s*\{([\s\S]*?)\n\}/g,
    // async function functionName() { ... }
    /async\s+function\s+(\w+)\s*\(\s*[^)]*\)\s*\{([\s\S]*?)\n\}/g,
  ];

  functionPatterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const functionName = match[1];
      const functionBody = match[2];

      // Vérifier si la fonction a une protection isMountedRef
      const hasIsMountedCheck = /if\s*\(\s*!\s*isMountedRef\.current\s*\)\s*return/.test(functionBody);
      const hasSetState = /set[A-Z]/.test(functionBody);

      functions.push({
        name: functionName,
        hasIsMountedCheck,
        hasSetState,
        body: functionBody.substring(0, 200), // Garder un extrait
      });
    }
  });

  return functions;
}

// Analyser un setTimeout pour voir s'il est protégé
function analyzeSetTimeout(content, filePath, functions) {
  const results = [];
  const lines = content.split('\n');

  lines.forEach((line, index) => {
    if (!line.includes('setTimeout')) return;

    const lineNumber = index + 1;

    // Extraire le contexte (5 lignes avant, 10 après)
    const contextStart = Math.max(0, index - 5);
    const contextEnd = Math.min(lines.length, index + 10);
    const context = lines.slice(contextStart, contextEnd).join('\n');

    // Vérifier si setState est appelé directement
    const hasDirectSetState = /set[A-Z]/.test(context);

    // Vérifier si une fonction est appelée
    let calledFunctions = [];
    const functionCallPattern = /(\w+)\s*\(/g;
    let match;
    while ((match = functionCallPattern.exec(context)) !== null) {
      const funcName = match[1];
      if (funcName !== 'setTimeout' && funcName !== 'if' && funcName !== 'return') {
        calledFunctions.push(funcName);
      }
    }

    // Vérifier la protection directe
    const hasDirectProtection = /if\s*\(\s*!\s*isMountedRef\.current\s*\)\s*return/.test(context);

    // Vérifier la protection dans les fonctions appelées
    let hasIndirectProtection = false;
    let protectedFunctions = [];

    calledFunctions.forEach(funcName => {
      const func = functions.find(f => f.name === funcName);
      if (func && func.hasIsMountedCheck) {
        hasIndirectProtection = true;
        protectedFunctions.push(funcName);
      }
    });

    // Déterminer si c'est dangereux
    const isDangerous = (hasDirectSetState || calledFunctions.some(name => {
      const func = functions.find(f => f.name === name);
      return func && func.hasSetState;
    })) && !hasDirectProtection && !hasIndirectProtection;

    if (hasDirectSetState || calledFunctions.length > 0) {
      results.push({
        lineNumber,
        isDangerous,
        hasDirectSetState,
        hasDirectProtection,
        hasIndirectProtection,
        calledFunctions,
        protectedFunctions,
        context: context.substring(0, 300),
      });
    }
  });

  return results;
}

// Analyser un fichier complet
function analyzeFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const relativePath = path.relative(frontendDir, filePath);

  // Vérifier si le fichier a isMountedRef
  const hasIsMountedRef = /isMountedRef/.test(content);

  // Extraire les fonctions
  const functions = extractFunctions(content, filePath);

  // Analyser les setTimeout
  const setTimeoutResults = analyzeSetTimeout(content, filePath, functions);

  if (setTimeoutResults.length === 0) return null;

  return {
    file: relativePath,
    hasIsMountedRef,
    functions,
    setTimeouts: setTimeoutResults,
  };
}

// Main
console.log('🔍 Analyse APPROFONDIE des setTimeout avec suivi de fonction...\n');
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
console.log(`\n📊 Résultats: ${results.length} fichiers avec setTimeout trouvés\n`);

let totalDangerous = 0;
let totalSafe = 0;

results.forEach((result, index) => {
  const dangerousSetTimeouts = result.setTimeouts.filter(st => st.isDangerous);
  const safeSetTimeouts = result.setTimeouts.filter(st => !st.isDangerous);

  totalDangerous += dangerousSetTimeouts.length;
  totalSafe += safeSetTimeouts.length;

  if (dangerousSetTimeouts.length > 0) {
    console.log(`\n${index + 1}. ⚠️  ${result.file}`);
    console.log(`   Has isMountedRef: ${result.hasIsMountedRef ? '✅' : '❌'}`);
    console.log(`   Fonctions trouvées: ${result.functions.length}`);
    console.log(`   setTimeout DANGEREUX: ${dangerousSetTimeouts.length}`);
    console.log(`   setTimeout SÛRS: ${safeSetTimeouts.length}`);

    dangerousSetTimeouts.forEach((timeout, i) => {
      console.log(`\n   ${i + 1}) Ligne ${timeout.lineNumber} - ❌ DANGER`);
      console.log(`      Direct setState: ${timeout.hasDirectSetState ? 'OUI' : 'NON'}`);
      console.log(`      Protection directe: ${timeout.hasDirectProtection ? 'OUI' : 'NON'}`);
      console.log(`      Fonctions appelées: ${timeout.calledFunctions.join(', ') || 'aucune'}`);
      console.log(`      Fonctions protégées: ${timeout.protectedFunctions.join(', ') || 'aucune'}`);
      console.log(`      Context: ${timeout.context.substring(0, 150)}...`);
    });

    console.log('\n' + '-'.repeat(80));
  }
});

// Résumé final
console.log(`\n\n🎯 RÉSUMÉ FINAL:`);
console.log('='.repeat(80));
console.log(`   Total fichiers analysés: ${files.length}`);
console.log(`   Fichiers avec setTimeout: ${results.length}`);
console.log(`   setTimeout DANGEREUX: ${totalDangerous} ❌`);
console.log(`   setTimeout SÛRS: ${totalSafe} ✅`);
console.log('='.repeat(80));

if (totalDangerous === 0) {
  console.log('\n✅ SUCCÈS: Aucun setTimeout dangereux détecté!');
  console.log('   Tous les setTimeout avec setState sont protégés.\n');
  process.exit(0);
} else {
  console.log(`\n⚠️  ATTENTION: ${totalDangerous} setTimeout dangereux détectés!`);
  console.log('   Veuillez ajouter des protections isMountedRef.\n');
  process.exit(1);
}
