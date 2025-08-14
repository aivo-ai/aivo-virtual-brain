#!/usr/bin/env node

console.log('🚀 Starting Stage-1 Readiness Gate Verification...');
console.log('='.repeat(60));

import { execSync } from 'child_process';

// Quick infrastructure check
console.log('🔍 Checking Docker Compose...');

try {
  const output = execSync('docker compose ps', { encoding: 'utf-8' });
  console.log('Docker Compose output:', output.substring(0, 200));
} catch (error) {
  console.log('❌ Docker Compose not running or available');
  console.log('💡 To start infrastructure: docker compose up -d');
}

// Test basic service connectivity
console.log('🏥 Testing basic service connectivity...');

import fetch from 'node-fetch';

const services = {
  'auth-svc': 'http://localhost:8000/health',
  'user-svc': 'http://localhost:8020/health', 
  'enrollment-router': 'http://localhost:8030/health',
};

let passed = 0;
let total = 0;

for (const [name, url] of Object.entries(services)) {
  total++;
  try {
    console.log(`  Testing ${name} at ${url}...`);
    const response = await fetch(url, { 
      signal: AbortSignal.timeout(2000)
    });
    
    if (response.ok) {
      console.log(`  ✅ ${name} - healthy`);
      passed++;
    } else {
      console.log(`  ❌ ${name} - HTTP ${response.status}`);
    }
  } catch (error) {
    console.log(`  ❌ ${name} - connection failed (${error.message})`);
  }
}

console.log('\n' + '='.repeat(60));
console.log(`📊 Quick Health Check: ${passed}/${total} services responding`);

if (passed === 0) {
  console.log('🚨 No services are running!');
  console.log('💡 Start services with: docker compose up -d');
  console.log('💡 Or run individual services manually');
} else if (passed === total) {
  console.log('🎉 All services are healthy!');
} else {
  console.log('⚠️  Some services are not responding');
}

console.log('='.repeat(60));
