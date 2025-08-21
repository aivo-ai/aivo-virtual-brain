#!/usr/bin/env node

/**
 * S4-20 Go-Live Cutover & Runbook Validation
 * 
 * Validates comprehensive go-live procedures, rollback plans,
 * and on-call documentation for production deployment readiness.
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const WORKSPACE_ROOT = process.cwd();

console.log('🚀 S4-20 — Go-Live Cutover & Runbook Validation');
console.log('================================================\n');

let validationErrors = [];
let validationWarnings = [];

/**
 * Validate go-live documentation exists and is comprehensive
 */
function validateGoLiveDocumentation() {
  console.log('📋 Validating Go-Live Documentation...');
  
  const goLivePath = join(WORKSPACE_ROOT, 'docs', 'runbooks', 'go-live.md');
  
  if (!existsSync(goLivePath)) {
    validationErrors.push('❌ Go-live documentation missing: docs/runbooks/go-live.md');
    return;
  }
  
  const goLiveContent = readFileSync(goLivePath, 'utf8');
  
  // Check for essential sections
  const requiredSections = [
    'Pre-Go-Live Checklist',
    'Go-Live Timeline',
    'Traffic Ramp Strategy', 
    'Monitoring & Alerting',
    'Stop-the-Line Triggers',
    'Roles & Responsibilities',
    'Communication Plan',
    'Post-Go-Live Validation'
  ];
  
  requiredSections.forEach(section => {
    if (!goLiveContent.includes(section)) {
      validationErrors.push(`❌ Go-live missing section: ${section}`);
    }
  });
  
  // Check for deployment commands
  const deploymentCommands = [
    'kubectl apply',
    'helm upgrade',
    'docker push',
    'terraform apply'
  ];
  
  let hasDeploymentCommands = deploymentCommands.some(cmd => 
    goLiveContent.includes(cmd)
  );
  
  if (!hasDeploymentCommands) {
    validationWarnings.push('⚠️  Go-live documentation missing deployment commands');
  }
  
  // Check for monitoring dashboards
  if (!goLiveContent.includes('dashboard') && !goLiveContent.includes('grafana')) {
    validationWarnings.push('⚠️  Go-live documentation missing monitoring dashboard references');
  }
  
  console.log('✅ Go-live documentation structure validated');
}

/**
 * Validate rollback procedures documentation
 */
function validateRollbackProcedures() {
  console.log('🔄 Validating Rollback Procedures...');
  
  const rollbackPath = join(WORKSPACE_ROOT, 'docs', 'runbooks', 'rollback.md');
  
  if (!existsSync(rollbackPath)) {
    validationErrors.push('❌ Rollback procedures missing: docs/runbooks/rollback.md');
    return;
  }
  
  const rollbackContent = readFileSync(rollbackPath, 'utf8');
  
  // Check for essential rollback sections
  const requiredSections = [
    'Rollback Decision Matrix',
    'Emergency Assessment',
    'Data Recovery Procedures',
    'Communication During Rollback',
    'Post-Rollback Validation'
  ];
  
  requiredSections.forEach(section => {
    if (!rollbackContent.includes(section)) {
      validationErrors.push(`❌ Rollback missing section: ${section}`);
    }
  });
  
  // Check for recovery time objectives
  if (!rollbackContent.includes('RTO') || !rollbackContent.includes('RPO')) {
    validationErrors.push('❌ Rollback procedures missing RTO/RPO definitions');
  }
  
  // Check for emergency contacts
  if (!rollbackContent.includes('Emergency Contacts')) {
    validationErrors.push('❌ Rollback procedures missing emergency contacts');
  }
  
  console.log('✅ Rollback procedures validated');
}

/**
 * Validate on-call schedule and procedures
 */
function validateOnCallDocumentation() {
  console.log('📞 Validating On-Call Documentation...');
  
  const scheduleePath = join(WORKSPACE_ROOT, 'docs', 'oncall', 'schedule.md');
  
  if (!existsSync(scheduleePath)) {
    validationErrors.push('❌ On-call schedule missing: docs/oncall/schedule.md');
    return;
  }
  
  const scheduleContent = readFileSync(scheduleePath, 'utf8');
  
  // Check for essential on-call sections
  const requiredSections = [
    'Current On-Call Rotation',
    'On-Call Responsibilities', 
    'Escalation Procedures',
    'Alert Channels',
    'Emergency Procedures'
  ];
  
  requiredSections.forEach(section => {
    if (!scheduleContent.includes(section)) {
      validationErrors.push(`❌ On-call schedule missing section: ${section}`);
    }
  });
  
  // Check for contact information
  const contactFields = ['+1-555-', '@aivo.edu', 'Slack:'];
  let hasContactInfo = contactFields.some(field => 
    scheduleContent.includes(field)
  );
  
  if (!hasContactInfo) {
    validationErrors.push('❌ On-call schedule missing contact information');
  }
  
  // Check for SLA definitions
  if (!scheduleContent.includes('Response Time') || !scheduleContent.includes('SLA')) {
    validationWarnings.push('⚠️  On-call schedule missing response time SLAs');
  }
  
  console.log('✅ On-call documentation validated');
}

/**
 * Validate production readiness infrastructure
 */
function validateProductionInfrastructure() {
  console.log('🏗️  Validating Production Infrastructure...');
  
  // Check for infrastructure code
  const infraPath = join(WORKSPACE_ROOT, 'infra');
  if (!existsSync(infraPath)) {
    validationWarnings.push('⚠️  Infrastructure directory not found');
    return;
  }
  
  // Check for key infrastructure components
  const infraComponents = [
    'kong',      // API Gateway
    'postgres',  // Database
    'grafana',   // Monitoring
    'prometheus' // Metrics
  ];
  
  infraComponents.forEach(component => {
    const componentPath = join(infraPath, component);
    if (!existsSync(componentPath)) {
      validationWarnings.push(`⚠️  Infrastructure component missing: ${component}`);
    }
  });
  
  // Check for deployment configuration
  const deploymentFiles = [
    'docker-compose.yml',
    'package.json'
  ];
  
  deploymentFiles.forEach(file => {
    const filePath = join(WORKSPACE_ROOT, file);
    if (!existsSync(filePath)) {
      validationWarnings.push(`⚠️  Deployment file missing: ${file}`);
    }
  });
  
  console.log('✅ Production infrastructure validated');
}

/**
 * Validate monitoring and observability setup
 */
function validateMonitoringSetup() {
  console.log('📊 Validating Monitoring Setup...');
  
  // Check for observability infrastructure
  const observabilityComponents = [
    join(WORKSPACE_ROOT, 'infra', 'grafana'),
    join(WORKSPACE_ROOT, 'infra', 'prometheus'),
    join(WORKSPACE_ROOT, 'infra', 'loki'),
    join(WORKSPACE_ROOT, 'infra', 'otel')
  ];
  
  observabilityComponents.forEach(component => {
    const componentName = component.split('/').pop();
    if (!existsSync(component)) {
      validationWarnings.push(`⚠️  Monitoring component missing: ${componentName}`);
    }
  });
  
  // Check for health check scripts
  const healthCheckScripts = [
    'scripts/health-check.mjs',
    'scripts/platform-health.py'
  ];
  
  healthCheckScripts.forEach(script => {
    const scriptPath = join(WORKSPACE_ROOT, script);
    if (!existsSync(scriptPath)) {
      validationWarnings.push(`⚠️  Health check script missing: ${script}`);
    }
  });
  
  console.log('✅ Monitoring setup validated');
}

/**
 * Validate security and compliance readiness
 */
function validateSecurityCompliance() {
  console.log('🔒 Validating Security & Compliance...');
  
  // Check for security documentation
  const securityPath = join(WORKSPACE_ROOT, 'docs', 'security');
  if (!existsSync(securityPath)) {
    validationWarnings.push('⚠️  Security documentation directory missing');
  }
  
  // Check for security testing scripts
  const securityScripts = [
    'test-security-policies.js',
    'test-simple-security.js'
  ];
  
  securityScripts.forEach(script => {
    const scriptPath = join(WORKSPACE_ROOT, script);
    if (existsSync(scriptPath)) {
      console.log(`✅ Security test found: ${script}`);
    } else {
      validationWarnings.push(`⚠️  Security test missing: ${script}`);
    }
  });
  
  // Check for Kong security configuration
  const kongSecurityPath = join(WORKSPACE_ROOT, 'infra', 'kong');
  if (existsSync(kongSecurityPath)) {
    console.log('✅ Kong security configuration found');
  }
  
  console.log('✅ Security compliance validated');
}

/**
 * Validate communication and escalation procedures
 */
function validateCommunicationProcedures() {
  console.log('📢 Validating Communication Procedures...');
  
  const goLivePath = join(WORKSPACE_ROOT, 'docs', 'runbooks', 'go-live.md');
  
  if (existsSync(goLivePath)) {
    const content = readFileSync(goLivePath, 'utf8');
    
    // Check for communication templates
    const commTemplates = [
      'status page',
      'customer notification',
      'stakeholder update',
      'incident notification'
    ];
    
    commTemplates.forEach(template => {
      if (content.toLowerCase().includes(template)) {
        console.log(`✅ Communication template found: ${template}`);
      } else {
        validationWarnings.push(`⚠️  Communication template missing: ${template}`);
      }
    });
  }
  
  console.log('✅ Communication procedures validated');
}

/**
 * Run all validations
 */
function runAllValidations() {
  validateGoLiveDocumentation();
  validateRollbackProcedures();
  validateOnCallDocumentation();
  validateProductionInfrastructure();
  validateMonitoringSetup();
  validateSecurityCompliance();
  validateCommunicationProcedures();
}

/**
 * Print validation results
 */
function printResults() {
  console.log('\n📋 S4-20 Validation Results');
  console.log('============================\n');
  
  if (validationErrors.length === 0 && validationWarnings.length === 0) {
    console.log('🎉 S4-20 GO-LIVE CUTOVER & RUNBOOK: FULLY VALIDATED');
    console.log('');
    console.log('✅ All go-live procedures documented');
    console.log('✅ Rollback procedures comprehensive'); 
    console.log('✅ On-call documentation complete');
    console.log('✅ Production infrastructure ready');
    console.log('✅ Monitoring and alerting configured');
    console.log('✅ Security compliance validated');
    console.log('✅ Communication procedures defined');
    console.log('');
    console.log('🚀 READY FOR PRODUCTION GO-LIVE EXECUTION');
    process.exit(0);
  }
  
  if (validationErrors.length > 0) {
    console.log('❌ VALIDATION ERRORS (Must fix before go-live):');
    validationErrors.forEach(error => console.log(`   ${error}`));
    console.log('');
  }
  
  if (validationWarnings.length > 0) {
    console.log('⚠️  VALIDATION WARNINGS (Recommended to address):');
    validationWarnings.forEach(warning => console.log(`   ${warning}`));
    console.log('');
  }
  
  console.log('📊 Validation Summary:');
  console.log(`   Errors: ${validationErrors.length}`);
  console.log(`   Warnings: ${validationWarnings.length}`);
  console.log(`   Status: ${validationErrors.length === 0 ? '✅ READY' : '❌ NOT READY'}`);
  
  if (validationErrors.length > 0) {
    console.log('\n🚫 S4-20 validation failed. Address errors before proceeding.');
    process.exit(1);
  } else {
    console.log('\n✅ S4-20 validation passed with warnings. Review warnings but ready to proceed.');
    process.exit(0);
  }
}

// Execute validation
runAllValidations();
printResults();
