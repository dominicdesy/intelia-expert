/**
 * Instrumentation file for Next.js
 * This file is automatically executed when the server starts
 * Useful for startup logs visible in Digital Ocean logs
 */

import packageJson from './package.json';

export async function register() {
  const version = packageJson.version;
  const environment = process.env.NODE_ENV || 'development';
  const timestamp = new Date().toISOString();

  console.log('\n' + '='.repeat(60));
  console.log('🚀 Intelia Expert Frontend - Starting up');
  console.log('='.repeat(60));
  console.log(`📦 Version: ${version}`);
  console.log(`🌍 Environment: ${environment}`);
  console.log(`⏰ Timestamp: ${timestamp}`);
  console.log(`🔧 Node version: ${process.version}`);
  console.log('='.repeat(60) + '\n');
}
