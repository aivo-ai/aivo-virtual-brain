#!/usr/bin/env node

/**
 * Simple health check script for Stage-2 services
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import fetch from 'node-fetch';

const execAsync = promisify(exec);

const services = [
  { name: 'auth-svc', port: 3001 },
  { name: 'user-svc', port: 3002 },
  { name: 'learner-svc', port: 3003 },
  { name: 'assessment-svc', port: 3004 },
  { name: 'slp-svc', port: 3005 },
  { name: 'inference-gateway-svc', port: 3006 },
  { name: 'search-svc', port: 3007 }
];

async function checkHealth() {
  console.log('🔍 Checking Stage-2 service health...\n');

  let healthyCount = 0;
  
  for (const service of services) {
    try {
      const response = await fetch(`http://localhost:${service.port}/health`, {
        timeout: 5000
      });
      
      if (response.ok) {
        console.log(`✅ ${service.name} - healthy (${response.status})`);
        healthyCount++;
      } else {
        console.log(`❌ ${service.name} - unhealthy (${response.status})`);
      }
    } catch (error) {
      console.log(`❌ ${service.name} - unreachable (${error.message})`);
    }
  }

  console.log(`\n📊 Health Summary: ${healthyCount}/${services.length} services healthy`);
  
  if (healthyCount === services.length) {
    console.log('🎉 All services are healthy!');
    process.exit(0);
  } else {
    console.log('⚠️  Some services are unhealthy');
    process.exit(1);
  }
}

checkHealth().catch(error => {
  console.error('Health check failed:', error);
  process.exit(1);
});
