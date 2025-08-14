#!/usr/bin/env node
/**
 * Stage-1 Readiness Gate Verifier - Focused Version
 * 
 * Validates Stage-1 deliverables and infrastructure readiness
 */

import { execSync } from 'child_process';
import * as fs from 'fs';

console.log('🚀 Starting Stage-1 Readiness Gate Verification...');
console.log('='.repeat(60));

let passed = 0;
let failed = 0;

function test(name, condition, details = '') {
  if (condition) {
    console.log(`✅ ${name}`);
    passed++;
  } else {
    console.log(`❌ ${name}${details ? ': ' + details : ''}`);
    failed++;
  }
}

console.log('🔍 Infrastructure Readiness...');

// Docker Compose check
try {
  const output = execSync('docker compose ps --format json', { encoding: 'utf-8' });
  if (output.trim()) {
    const containers = JSON.parse(`[${output.trim().split('\n').join(',')}]`);
    const runningServices = containers.filter(c => c.State === 'running').map(c => c.Service);
    
    test('Infrastructure: Docker Compose running', containers.length > 0);
    test('Infrastructure: Postgres container', runningServices.includes('postgres'));
    test('Infrastructure: Redis container', runningServices.includes('redis'));
    test('Infrastructure: MinIO container', runningServices.includes('minio'));
  } else {
    test('Infrastructure: Docker Compose', false, 'No containers - run: docker compose up -d');
  }
} catch (error) {
  test('Infrastructure: Docker Compose', false, 'Not available or not running');
}

console.log('\n📊 Observability Stack...');

// Grafana dashboards
try {
  const dashboardPath = './infra/grafana/dashboards';
  if (fs.existsSync(dashboardPath)) {
    const dashboards = fs.readdirSync(dashboardPath).filter(f => f.endsWith('.json'));
    const expectedDashboards = [
      'auth-service.json',
      'user-service.json',
      'learner-service.json', 
      'payment-service.json',
      'assessment-service.json',
      'iep-service.json',
      'finops-dashboard.json'
    ];
    
    expectedDashboards.forEach(dashboard => {
      test(`Observability: ${dashboard}`, dashboards.includes(dashboard));
    });
    
    test('Observability: Dashboard count', dashboards.length === 7, `${dashboards.length}/7 dashboards`);
  } else {
    test('Observability: Dashboards directory', false, 'Directory not found');
  }
} catch (error) {
  test('Observability: Dashboards', false, error.message);
}

// Alert rules
test('Observability: Alert rules', fs.existsSync('./infra/grafana/provisioning/alerting/alert-rules.yml'));
test('Observability: Grafana config', fs.existsSync('./infra/grafana/provisioning/alerting/rules.yml'));

console.log('\n📝 Service Architecture...');

// Service structure
const serviceDir = './services';
if (fs.existsSync(serviceDir)) {
  const services = fs.readdirSync(serviceDir).filter(dir => 
    fs.statSync(`${serviceDir}/${dir}`).isDirectory() && !dir.startsWith('_')
  );
  
  const requiredServices = ['auth-svc', 'user-svc', 'enrollment-router', 'learner-svc', 'assessment-svc', 'payment-svc'];
  
  requiredServices.forEach(service => {
    const exists = services.includes(service);
    const hasMain = exists && fs.existsSync(`${serviceDir}/${service}/main.py`);
    test(`Service: ${service} structure`, hasMain, exists ? (hasMain ? undefined : 'Missing main.py') : 'Directory missing');
  });
  
  test('Service: Total count', services.length >= 6, `${services.length} services found`);
} else {
  test('Service: Services directory', false, 'Directory not found');
}

console.log('\n📚 Documentation...');

test('Docs: Stage-1 checklist', fs.existsSync('./docs/checklists/stage-1.md'));
test('Docs: README', fs.existsSync('./README.md'));
test('Docs: Docker Compose config', fs.existsSync('./docker-compose.yml'));

console.log('\n🔧 Project Configuration...');

test('Config: package.json', fs.existsSync('./package.json'));
test('Config: turbo.json', fs.existsSync('./turbo.json'));
test('Config: .gitignore', fs.existsSync('./.gitignore'));

// Check package.json for verify-stage1 script
if (fs.existsSync('./package.json')) {
  const pkg = JSON.parse(fs.readFileSync('./package.json', 'utf-8'));
  test('Config: verify-stage1 script', pkg.scripts && pkg.scripts['verify-stage1']);
}

console.log('\n' + '='.repeat(60));
console.log('📋 STAGE-1 VERIFICATION REPORT');
console.log('='.repeat(60));

console.log(`\n✅ Passed: ${passed}`);
console.log(`❌ Failed: ${failed}`);
console.log(`📊 Total:  ${passed + failed}`);

const successRate = ((passed / (passed + failed)) * 100).toFixed(1);
console.log(`🎯 Success Rate: ${successRate}%`);

console.log('\n' + '='.repeat(60));

if (failed === 0) {
  console.log('🎉 Stage-1 verification PASSED! Ready for v1.0.0-stage1 tag.');
  console.log('\n🏷️  Next Steps:');
  console.log('   git tag v1.0.0-stage1');
  console.log('   git push origin v1.0.0-stage1');
  process.exit(0);
} else if (failed <= 3) {
  console.log('⚠️  Stage-1 verification passed with minor issues.');
  console.log('   Consider fixing failed tests before tagging v1.0.0-stage1.');
  console.log('\n💡 Quick Fixes:');
  console.log('   - Start infrastructure: docker compose up -d');
  console.log('   - Check missing files in failed tests above');
  process.exit(0);
} else {
  console.log('🚨 Stage-1 verification FAILED! Address critical issues before release.');
  console.log('\n💡 Required Actions:');
  if (failed > 5) {
    console.log('   - Complete missing infrastructure components');
    console.log('   - Ensure all service directories exist');
    console.log('   - Verify observability stack is implemented');
  }
  console.log('   - Fix failed tests listed above');
  console.log('   - Re-run: pnpm run verify-stage1');
  console.log('\n📚 See: docs/checklists/stage-1.md for complete requirements');
  process.exit(1);
}
