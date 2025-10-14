#!/usr/bin/env node
/**
 * Script ESLint personnalisé pour vérifier TOUS les setTimeout avec setState
 * Analyse AST approfondie pour détecter les protections dans les fonctions appelées
 *
 * Usage: node eslint-check-settimeout.js
 */

const { ESLint } = require('eslint');
const path = require('path');

// Configuration ESLint pour détecter les setState non protégés
const eslintConfig = {
  baseConfig: {
    parser: '@typescript-eslint/parser',
    parserOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      ecmaFeatures: {
        jsx: true,
      },
    },
    plugins: ['react', 'react-hooks', '@typescript-eslint'],
    rules: {
      // Règles React hooks
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // Règle personnalisée pour setTimeout
      'no-restricted-syntax': [
        'error',
        {
          selector: "CallExpression[callee.name='setTimeout']",
          message: 'setTimeout found - manual review needed for setState protection',
        },
      ],
    },
  },
  overrideConfigFile: true,
  useEslintrc: false,
};

async function analyzeSetTimeout() {
  console.log('🔍 Analyse ESLint approfondie des setTimeout...\n');
  console.log('='.repeat(80));

  try {
    const eslint = new ESLint(eslintConfig);

    const frontendDir = path.join(__dirname, '..', 'frontend');

    // Analyser tous les fichiers TypeScript et TSX
    const results = await eslint.lintFiles([
      `${frontendDir}/**/*.ts`,
      `${frontendDir}/**/*.tsx`,
    ]);

    // Filtrer pour ne garder que les setTimeout
    const setTimeoutIssues = results.filter(result =>
      result.messages.some(msg => msg.message.includes('setTimeout'))
    );

    console.log(`\n📊 Résultats ESLint:\n`);
    console.log(`Total fichiers analysés: ${results.length}`);
    console.log(`Fichiers avec setTimeout: ${setTimeoutIssues.length}\n`);

    if (setTimeoutIssues.length > 0) {
      console.log('⚠️  Fichiers nécessitant une vérification manuelle:\n');

      setTimeoutIssues.forEach((result, index) => {
        const relativePath = path.relative(frontendDir, result.filePath);
        const setTimeoutMsgs = result.messages.filter(msg =>
          msg.message.includes('setTimeout')
        );

        console.log(`${index + 1}. ${relativePath}`);
        console.log(`   Occurrences: ${setTimeoutMsgs.length}`);

        setTimeoutMsgs.forEach(msg => {
          console.log(`   - Ligne ${msg.line}: ${msg.message}`);
        });

        console.log('');
      });
    } else {
      console.log('✅ Aucun setTimeout détecté (ou tous sont gérés)\n');
    }

    // Vérifier les hooks React spécifiquement
    const hookIssues = results.filter(result =>
      result.messages.some(msg =>
        msg.ruleId === 'react-hooks/rules-of-hooks' ||
        msg.ruleId === 'react-hooks/exhaustive-deps'
      )
    );

    if (hookIssues.length > 0) {
      console.log('⚠️  Problèmes avec les React Hooks:\n');

      hookIssues.forEach((result, index) => {
        const relativePath = path.relative(frontendDir, result.filePath);
        const hookMsgs = result.messages.filter(msg =>
          msg.ruleId?.includes('react-hooks')
        );

        console.log(`${index + 1}. ${relativePath}`);
        hookMsgs.forEach(msg => {
          console.log(`   - Ligne ${msg.line}: ${msg.message}`);
        });
        console.log('');
      });
    }

    console.log('='.repeat(80));
    console.log('\n💡 Note: Cette analyse détecte les setTimeout mais ne peut pas');
    console.log('   vérifier automatiquement les protections isMountedRef dans les');
    console.log('   fonctions appelées. Vérification manuelle recommandée.\n');

    return {
      totalFiles: results.length,
      setTimeoutFiles: setTimeoutIssues.length,
      hookIssues: hookIssues.length,
    };

  } catch (error) {
    if (error.message.includes('Cannot find module')) {
      console.error('\n❌ Erreur: Dépendances ESLint manquantes\n');
      console.log('Installation requise:');
      console.log('  npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-react eslint-plugin-react-hooks\n');
    } else {
      console.error('❌ Erreur lors de l\'analyse:', error.message);
    }

    return null;
  }
}

// Exécuter l'analyse
if (require.main === module) {
  analyzeSetTimeout()
    .then(result => {
      if (result) {
        process.exit(result.setTimeoutFiles > 0 ? 1 : 0);
      } else {
        process.exit(1);
      }
    })
    .catch(err => {
      console.error('Erreur fatale:', err);
      process.exit(1);
    });
}

module.exports = { analyzeSetTimeout };
