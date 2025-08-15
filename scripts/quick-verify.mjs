#!/usr/bin/env node

/**
 * Quick Platform Verification
 * Tests all AIVO services are running and responsive
 */

import axios from 'axios';

const services = [
  { name: 'auth-svc', port: 3001, path: '/health' },
  { name: 'user-svc', port: 3002, path: '/health' }, 
  { name: 'assessment-svc', port: 3004, path: '/health' },
  { name: 'slp-svc', port: 3005, path: '/health' },
  { name: 'inference-gateway-svc', port: 3006, path: '/health' },
  { name: 'search-svc', port: 3007, path: '/health' }
];

async function testService(service) {
  try {
    const response = await axios.get(`http://localhost:${service.port}${service.path}`, { 
      timeout: 3000 
    });
    
    return {
      name: service.name,
      port: service.port,
      status: 'healthy',
      service_name: response.data.service,
      response_time: Date.now()
    };
  } catch (error) {
    return {
      name: service.name,
      port: service.port, 
      status: 'unhealthy',
      error: error.message
    };
  }
}

async function runQuickVerification() {
  console.log('🚀 AIVO Platform Quick Verification');
  console.log('==================================');
  console.log();

  // Test all services
  console.log('🔍 Testing microservices...');
  const results = await Promise.allSettled(
    services.map(service => testService(service))
  );

  const serviceResults = results.map(result => 
    result.status === 'fulfilled' ? result.value : { status: 'failed', error: result.reason }
  );

  // Display results
  let healthyCount = 0;
  serviceResults.forEach(result => {
    if (result.status === 'healthy') {
      console.log(`  ✅ ${result.name} (port ${result.port}): ${result.service_name || 'OK'}`);
      healthyCount++;
    } else {
      console.log(`  ❌ ${result.name} (port ${result.port}): ${result.error || 'Failed'}`);
    }
  });

  console.log();
  console.log(`📊 Results: ${healthyCount}/${services.length} services healthy`);
  
  if (healthyCount === services.length) {
    console.log('🎉 All services are running successfully!');
    console.log();
    console.log('🌐 Available endpoints:');
    services.forEach(service => {
      console.log(`   • ${service.name}: http://localhost:${service.port}`);
    });
    
    return true;
  } else {
    console.log('⚠️  Some services are not responding');
    return false;
  }
}

// Test a simple workflow
async function testWorkflow() {
  console.log();
  console.log('🧪 Testing basic workflow...');
  
  try {
    // Test search service
    const searchResponse = await axios.get('http://localhost:3007/search?q=machine%20learning', {
      timeout: 5000
    });
    console.log('  ✅ Search functionality working');
    
    // Test auth service  
    const authResponse = await axios.post('http://localhost:3001/auth/login', {
      email: 'test@example.com',
      password: 'testpass'
    }, { timeout: 5000 });
    console.log('  ✅ Authentication working');
    
    console.log('🎉 Basic workflow test passed!');
    return true;
  } catch (error) {
    console.log(`  ❌ Workflow test failed: ${error.message}`);
    return false;
  }
}

// Main execution
async function main() {
  const servicesHealthy = await runQuickVerification();
  
  if (servicesHealthy) {
    const workflowPassed = await testWorkflow();
    process.exit(workflowPassed ? 0 : 1);
  } else {
    process.exit(1);
  }
}

main().catch(error => {
  console.error('Verification failed:', error);
  process.exit(1);
});
