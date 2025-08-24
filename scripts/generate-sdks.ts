#!/usr/bin/env tsx
/**
 * SDK Generation Script for AIVO Platform
 * Generates TypeScript/JavaScript and Python SDKs from OpenAPI specifications
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { execSync } from 'child_process';
import { glob } from 'glob';

interface SDKConfig {
  name: string;
  spec: string;
  outputDir: string;
  language: 'typescript' | 'python';
  packageName?: string;
  additionalProperties?: Record<string, string>;
}

const SDK_CONFIGS: SDKConfig[] = [
  // TypeScript/JavaScript SDKs
  {
    name: 'chat-sdk-web',
    spec: 'docs/api/rest/chat.yaml',
    outputDir: 'libs/sdk-web/src/chat',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/chat-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },
  {
    name: 'scim-sdk-web',
    spec: 'docs/api/rest/scim.yaml',
    outputDir: 'libs/sdk-web/src/scim',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/scim-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },
  {
    name: 'sis-bridge-sdk-web',
    spec: 'docs/api/rest/sis-bridge.yaml',
    outputDir: 'libs/sdk-web/src/sis',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/sis-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },
  {
    name: 'verification-sdk-web',
    spec: 'docs/api/rest/verification.yaml',
    outputDir: 'libs/sdk-web/src/verification',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/verification-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },
  {
    name: 'tax-sdk-web',
    spec: 'docs/api/rest/tax.yaml',
    outputDir: 'libs/sdk-web/src/tax',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/tax-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },
  {
    name: 'residency-sdk-web',
    spec: 'docs/api/rest/residency.yaml',
    outputDir: 'libs/sdk-web/src/residency',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/residency-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },
  {
    name: 'compliance-sdk-web',
    spec: 'docs/api/rest/compliance.yaml',
    outputDir: 'libs/sdk-web/src/compliance',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/compliance-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },
  {
    name: 'legal-hold-sdk-web',
    spec: 'docs/api/rest/legal-hold.yaml',
    outputDir: 'libs/sdk-web/src/legal',
    language: 'typescript',
    additionalProperties: {
      npmName: '@aivo/legal-hold-sdk',
      supportsES6: 'true',
      withInterfaces: 'true',
    }
  },

  // Python SDKs
  {
    name: 'chat-sdk-py',
    spec: 'docs/api/rest/chat.yaml',
    outputDir: 'libs/sdk-py/aivo_sdk/chat',
    language: 'python',
    packageName: 'aivo-chat-sdk',
    additionalProperties: {
      packageName: 'aivo_chat_sdk',
      projectName: 'aivo-chat-sdk',
      packageVersion: '1.0.0',
      packageDescription: 'AIVO Chat Service Python SDK',
    }
  },
  {
    name: 'scim-sdk-py',
    spec: 'docs/api/rest/scim.yaml',
    outputDir: 'libs/sdk-py/aivo_sdk/scim',
    language: 'python',
    packageName: 'aivo-scim-sdk',
    additionalProperties: {
      packageName: 'aivo_scim_sdk',
      projectName: 'aivo-scim-sdk',
      packageVersion: '1.0.0',
      packageDescription: 'AIVO SCIM 2.0 Python SDK',
    }
  },
  {
    name: 'verification-sdk-py',
    spec: 'docs/api/rest/verification.yaml',
    outputDir: 'libs/sdk-py/aivo_sdk/verification',
    language: 'python',
    packageName: 'aivo-verification-sdk',
    additionalProperties: {
      packageName: 'aivo_verification_sdk',
      projectName: 'aivo-verification-sdk',
      packageVersion: '1.0.0',
      packageDescription: 'AIVO Guardian Verification Python SDK',
    }
  },
  {
    name: 'legal-hold-sdk-py',
    spec: 'docs/api/rest/legal-hold.yaml',
    outputDir: 'libs/sdk-py/aivo_sdk/legal_hold',
    language: 'python',
    packageName: 'aivo-legal-hold-sdk',
    additionalProperties: {
      packageName: 'aivo_legal_hold_sdk',
      projectName: 'aivo-legal-hold-sdk',
      packageVersion: '1.0.0',
      packageDescription: 'AIVO Legal Hold & eDiscovery Python SDK',
    }
  }
];

async function ensureDirectoryExists(dir: string): Promise<void> {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

async function generateSDK(config: SDKConfig): Promise<void> {
  console.log(`Generating ${config.language} SDK for ${config.name}...`);

  // Check if spec file exists
  if (!existsSync(config.spec)) {
    console.warn(`⚠️  Spec file not found: ${config.spec}. Skipping ${config.name}.`);
    return;
  }

  // Ensure output directory exists
  await ensureDirectoryExists(config.outputDir);

  // Prepare OpenAPI Generator command
  const generator = config.language === 'typescript' ? 'typescript-fetch' : 'python';
  
  let command = [
    'npx', '@openapitools/openapi-generator-cli', 'generate',
    `-i`, config.spec,
    `-g`, generator,
    `-o`, config.outputDir,
    `--skip-validate-spec`
  ];

  // Add additional properties
  if (config.additionalProperties) {
    const props = Object.entries(config.additionalProperties)
      .map(([key, value]) => `${key}=${value}`)
      .join(',');
    command.push('--additional-properties', props);
  }

  // Add language-specific configurations
  if (config.language === 'typescript') {
    command.push(
      '--type-mappings', 'DateTime=Date',
      '--import-mappings', 'DateTime=Date',
      '--additional-properties', 'usePromises=true,useInversify=false,useObjectParameters=true'
    );
  } else if (config.language === 'python') {
    command.push(
      '--additional-properties', 'generateSourceCodeOnly=true,library=urllib3'
    );
  }

  try {
    // Generate SDK
    execSync(command.join(' '), { 
      stdio: 'inherit',
      cwd: process.cwd()
    });

    // Post-processing for TypeScript SDKs
    if (config.language === 'typescript') {
      await postProcessTypeScriptSDK(config);
    } else if (config.language === 'python') {
      await postProcessPythonSDK(config);
    }

    console.log(`✅ Generated ${config.name} successfully`);
  } catch (error) {
    console.error(`❌ Failed to generate ${config.name}:`, error);
    throw error;
  }
}

async function postProcessTypeScriptSDK(config: SDKConfig): Promise<void> {
  // Create index.ts file for easier imports
  const indexPath = join(config.outputDir, 'index.ts');
  const indexContent = `
// Auto-generated SDK exports for ${config.name}
export * from './api';
export * from './configuration';
export * from './models';

// Re-export commonly used types
export type { Configuration, ConfigurationParameters } from './configuration';
`;

  writeFileSync(indexPath, indexContent.trim());

  // Create package.json if it doesn't exist
  const packageJsonPath = join(dirname(config.outputDir), 'package.json');
  if (!existsSync(packageJsonPath)) {
    const packageJson = {
      name: config.additionalProperties?.npmName || config.name,
      version: '1.0.0',
      description: `TypeScript SDK for ${config.name}`,
      main: 'dist/index.js',
      types: 'dist/index.d.ts',
      scripts: {
        build: 'tsc',
        test: 'jest'
      },
      dependencies: {
        'cross-fetch': '^3.1.8'
      },
      devDependencies: {
        'typescript': '^5.0.0',
        '@types/node': '^20.0.0'
      }
    };

    writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));
  }
}

async function postProcessPythonSDK(config: SDKConfig): Promise<void> {
  // Create __init__.py file
  const initPath = join(config.outputDir, '__init__.py');
  const initContent = `
"""
${config.packageName || config.name} Python SDK
Auto-generated client for AIVO Platform APIs
"""

from .api_client import ApiClient
from .configuration import Configuration
from .exceptions import ApiException, ApiValueError

__version__ = "1.0.0"
__all__ = ["ApiClient", "Configuration", "ApiException", "ApiValueError"]
`;

  writeFileSync(initPath, initContent.trim());

  // Create setup.py if it doesn't exist
  const setupPath = join(dirname(dirname(config.outputDir)), 'setup.py');
  if (!existsSync(setupPath)) {
    const setupContent = `
from setuptools import setup, find_packages

setup(
    name="${config.packageName || config.name}",
    version="1.0.0",
    description="${config.additionalProperties?.packageDescription || 'AIVO Platform Python SDK'}",
    packages=find_packages(),
    install_requires=[
        "urllib3>=1.26.0",
        "python-dateutil>=2.8.0",
        "pydantic>=1.10.0"
    ],
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
`;

    writeFileSync(setupPath, setupContent.trim());
  }
}

async function generateAllSDKs(): Promise<void> {
  console.log('🚀 Starting SDK generation for AIVO Platform...\n');

  // Install OpenAPI Generator CLI if not present
  try {
    execSync('npx @openapitools/openapi-generator-cli version-manager set 7.1.0', { stdio: 'inherit' });
  } catch (error) {
    console.log('Installing OpenAPI Generator CLI...');
    execSync('npm install -g @openapitools/openapi-generator-cli', { stdio: 'inherit' });
  }

  let successCount = 0;
  let failureCount = 0;

  for (const config of SDK_CONFIGS) {
    try {
      await generateSDK(config);
      successCount++;
    } catch (error) {
      console.error(`Failed to generate ${config.name}`);
      failureCount++;
    }
  }

  console.log(`\n📊 SDK Generation Summary:`);
  console.log(`✅ Successful: ${successCount}`);
  console.log(`❌ Failed: ${failureCount}`);
  console.log(`📦 Total: ${SDK_CONFIGS.length}`);

  if (failureCount > 0) {
    process.exit(1);
  }
}

// Generate a unified web SDK index
async function generateUnifiedWebSDK(): Promise<void> {
  const webSDKDir = 'libs/sdk-web/src';
  const unifiedIndexPath = join(webSDKDir, 'index.ts');

  const unifiedContent = `
/**
 * AIVO Platform Unified Web SDK
 * Auto-generated unified exports for all AIVO services
 */

// Chat SDK
export * as ChatSDK from './chat';

// SCIM SDK  
export * as SCIMDK from './scim';

// SIS Bridge SDK
export * as SISSDK from './sis';

// Verification SDK
export * as VerificationSDK from './verification';

// Tax SDK
export * as TaxSDK from './tax';

// Residency SDK
export * as ResidencySDK from './residency';

// Compliance SDK
export * as ComplianceSDK from './compliance';

// Legal Hold SDK
export * as LegalHoldSDK from './legal';

// Re-export common types
export type { Configuration, ConfigurationParameters } from './chat/configuration';

// SDK version
export const SDK_VERSION = '1.0.0';

// Default configuration factory
export function createConfiguration(params: {
  basePath?: string;
  apiKey?: string;
  bearerToken?: string;
}): Configuration {
  return new Configuration({
    basePath: params.basePath || 'https://api.aivo.io',
    apiKey: params.apiKey,
    accessToken: params.bearerToken,
  });
}
`;

  await ensureDirectoryExists(webSDKDir);
  writeFileSync(unifiedIndexPath, unifiedContent.trim());
  console.log('✅ Generated unified web SDK index');
}

// Main execution
async function main(): Promise<void> {
  try {
    await generateAllSDKs();
    await generateUnifiedWebSDK();
    console.log('\n🎉 All SDKs generated successfully!');
  } catch (error) {
    console.error('❌ SDK generation failed:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

export { generateAllSDKs, generateSDK, SDK_CONFIGS };
