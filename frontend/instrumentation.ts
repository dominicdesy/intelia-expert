/**
 * Instrumentation file for Next.js
 * This file is automatically executed when the server starts
 * Useful for startup logs visible in Digital Ocean logs
 */

import packageJson from './package.json';
import { secureLog } from "@/lib/utils/secureLogger";

export async function register() {
  const version = packageJson.version;
  const environment = process.env.NODE_ENV || 'development';
  const timestamp = new Date().toISOString();

  secureLog.log('\n' + '='.repeat(60));
  secureLog.log('🚀 Intelia Expert Frontend - Starting up');
  secureLog.log('='.repeat(60));
  secureLog.log(`📦 Version: ${version}`);
  secureLog.log(`🌍 Environment: ${environment}`);
  secureLog.log(`⏰ Timestamp: ${timestamp}`);
  secureLog.log(`🔧 Node version: ${process.version}`);
  secureLog.log('='.repeat(60) + '\n');
}
