import { http, HttpResponse } from 'msw';
import { faker } from '@faker-js/faker';

// Residency Verification API Mock Handlers  
export const residencyHandlers = [
  // Start residency verification
  http.post('/api/residency/verify', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      user_id: body.user_id,
      status: 'pending_documents',
      verification_type: body.verification_type || 'parent_guardian',
      required_documents: [
        'utility_bill',
        'bank_statement', 
        'lease_agreement'
      ],
      submitted_documents: [],
      address: {
        street: body.address?.street,
        city: body.address?.city,
        state: body.address?.state,
        zip_code: body.address?.zip_code,
        country: body.address?.country || 'US',
      },
      progress: {
        current_step: 'document_submission',
        total_steps: 4,
        completed_steps: 1,
      },
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Get verification status
  http.get('/api/residency/verify/:verificationId', ({ params }) => {
    const status = faker.helpers.arrayElement([
      'pending_documents', 'documents_submitted', 'under_review', 
      'approved', 'rejected', 'expired'
    ]);
    
    return HttpResponse.json({
      id: params.verificationId,
      user_id: faker.string.uuid(),
      status,
      verification_type: 'parent_guardian',
      required_documents: ['utility_bill', 'bank_statement', 'lease_agreement'],
      submitted_documents: status !== 'pending_documents' ? [
        {
          id: faker.string.uuid(),
          document_type: 'utility_bill',
          filename: 'electric_bill_march_2024.pdf',
          status: 'verified',
          submitted_at: faker.date.recent().toISOString(),
          verified_at: faker.date.recent().toISOString(),
          extracted_data: {
            service_address: {
              street: '123 Main Street',
              city: 'San Francisco',
              state: 'CA',
              zip_code: '94102',
            },
            service_date: '2024-03-15',
            account_holder: faker.person.fullName(),
          },
        }
      ] : [],
      address: {
        street: '123 Main Street',
        city: 'San Francisco', 
        state: 'CA',
        zip_code: '94102',
        country: 'US',
      },
      verification_result: status === 'approved' ? {
        decision: 'approved',
        confidence_score: 0.95,
        verified_address: {
          street: '123 Main Street',
          city: 'San Francisco',
          state: 'CA', 
          zip_code: '94102',
          country: 'US',
        },
        school_district: {
          name: 'San Francisco Unified School District',
          code: 'SFUSD',
          boundaries_confirmed: true,
        },
        approved_at: faker.date.recent().toISOString(),
        valid_until: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
      } : undefined,
      progress: {
        current_step: status,
        total_steps: 4,
        completed_steps: status === 'approved' ? 4 : 2,
      },
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: faker.date.past().toISOString(),
      updated_at: faker.date.recent().toISOString(),
    });
  }),

  // Submit document
  http.post('/api/residency/verify/:verificationId/documents', async ({ params, request }) => {
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      document_type: 'utility_bill',
      filename: 'electric_bill_march_2024.pdf',
      status: 'processing',
      file_url: faker.internet.url(),
      extracted_data: {
        service_address: {
          street: '123 Main Street',
          city: 'San Francisco',
          state: 'CA',
          zip_code: '94102',
        },
        service_date: '2024-03-15',
        account_holder: faker.person.fullName(),
        utility_company: 'PG&E',
        account_number: faker.string.alphanumeric(12),
      },
      confidence_score: faker.number.float({ min: 0.85, max: 1.0 }),
      submitted_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Check school district boundaries
  http.get('/api/residency/districts/lookup', ({ request }) => {
    const url = new URL(request.url);
    const address = url.searchParams.get('address');
    
    return HttpResponse.json({
      address: address || '123 Main Street, San Francisco, CA 94102',
      school_districts: [
        {
          name: 'San Francisco Unified School District',
          code: 'SFUSD',
          type: 'unified',
          grade_levels: ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'],
          boundaries_confirmed: true,
          enrollment_open: true,
          contact_info: {
            phone: '(415) 241-6000',
            website: 'https://www.sfusd.edu',
            enrollment_office: '555 Franklin Street, San Francisco, CA 94102',
          },
        }
      ],
      boundary_confidence: 0.98,
    });
  }),
];

// SIS Bridge API Mock Handlers
export const sisBridgeHandlers = [
  // List SIS connections
  http.get('/api/sis/connections', ({ request }) => {
    const url = new URL(request.url);
    const tenant_id = url.searchParams.get('tenant_id');
    
    const connections = Array.from({ length: 3 }, () => ({
      id: faker.string.uuid(),
      tenant_id: tenant_id || faker.string.uuid(),
      sis_provider: faker.helpers.arrayElement(['powerschool', 'infinite_campus', 'skyward', 'clever', 'google_classroom']),
      connection_name: faker.company.name() + ' SIS',
      status: faker.helpers.arrayElement(['active', 'inactive', 'error', 'syncing']),
      sync_settings: {
        auto_sync_enabled: faker.datatype.boolean(),
        sync_frequency: faker.helpers.arrayElement(['hourly', 'daily', 'weekly']),
        sync_types: ['students', 'teachers', 'classes', 'enrollments', 'grades'],
        last_sync: faker.date.recent().toISOString(),
        next_sync: faker.date.future().toISOString(),
      },
      field_mappings: {
        student_id: 'student_number',
        first_name: 'first_name',
        last_name: 'last_name',
        email: 'email_addr',
        grade_level: 'grade_level',
      },
      created_at: faker.date.past().toISOString(),
      updated_at: faker.date.recent().toISOString(),
    }));
    
    return HttpResponse.json({ connections });
  }),

  // Create SIS connection
  http.post('/api/sis/connections', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      tenant_id: body.tenant_id,
      sis_provider: body.sis_provider,
      connection_name: body.connection_name,
      status: 'inactive',
      sync_settings: {
        auto_sync_enabled: false,
        sync_frequency: 'daily',
        sync_types: body.sync_types || ['students', 'teachers'],
        last_sync: null,
        next_sync: null,
      },
      field_mappings: body.field_mappings || {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Test SIS connection
  http.post('/api/sis/connections/:connectionId/test', async ({ params }) => {
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const success = faker.datatype.boolean();
    
    return HttpResponse.json({
      connection_id: params.connectionId,
      test_status: success ? 'success' : 'failed',
      test_results: {
        authentication: success,
        api_access: success,
        data_retrieval: success,
        sample_records: success ? faker.number.int({ min: 10, max: 100 }) : 0,
      },
      error_message: success ? null : 'Invalid API credentials',
      tested_at: new Date().toISOString(),
    });
  }),

  // Sync data
  http.post('/api/sis/connections/:connectionId/sync', async ({ params, request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      sync_id: faker.string.uuid(),
      connection_id: params.connectionId,
      sync_type: body.sync_type || 'full',
      status: 'in_progress',
      progress: {
        current_stage: 'fetching_students',
        total_stages: 5,
        completed_stages: 1,
        percentage: 20,
      },
      statistics: {
        students_processed: 0,
        teachers_processed: 0,
        classes_processed: 0,
        enrollments_processed: 0,
        errors: 0,
      },
      started_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Get sync status
  http.get('/api/sis/sync/:syncId', ({ params }) => {
    const status = faker.helpers.arrayElement(['in_progress', 'completed', 'failed', 'cancelled']);
    
    return HttpResponse.json({
      sync_id: params.syncId,
      connection_id: faker.string.uuid(),
      sync_type: 'full',
      status,
      progress: {
        current_stage: status === 'completed' ? 'completed' : 'processing_enrollments',
        total_stages: 5,
        completed_stages: status === 'completed' ? 5 : 3,
        percentage: status === 'completed' ? 100 : 60,
      },
      statistics: {
        students_processed: faker.number.int({ min: 100, max: 1000 }),
        teachers_processed: faker.number.int({ min: 10, max: 100 }),
        classes_processed: faker.number.int({ min: 50, max: 200 }),
        enrollments_processed: faker.number.int({ min: 500, max: 5000 }),
        errors: faker.number.int({ min: 0, max: 5 }),
      },
      started_at: faker.date.recent().toISOString(),
      completed_at: status === 'completed' ? faker.date.recent().toISOString() : null,
      error_message: status === 'failed' ? 'Connection timeout during enrollment sync' : null,
    });
  }),

  // Get sync logs
  http.get('/api/sis/sync/:syncId/logs', ({ params, request }) => {
    const url = new URL(request.url);
    const level = url.searchParams.get('level');
    
    const logs = Array.from({ length: 20 }, () => {
      const logLevel = level || faker.helpers.arrayElement(['info', 'warn', 'error']);
      return {
        id: faker.string.uuid(),
        sync_id: params.syncId,
        level: logLevel,
        message: faker.helpers.arrayElement([
          'Successfully processed student record',
          'Duplicate teacher email detected, skipping',
          'Invalid grade level value, using default',
          'Class enrollment sync completed',
          'API rate limit reached, retrying',
        ]),
        details: {
          record_id: faker.string.uuid(),
          record_type: faker.helpers.arrayElement(['student', 'teacher', 'class', 'enrollment']),
          sis_id: faker.string.alphanumeric(8),
        },
        timestamp: faker.date.recent().toISOString(),
      };
    });
    
    return HttpResponse.json({ logs });
  }),

  // List supported SIS providers
  http.get('/api/sis/providers', () => {
    return HttpResponse.json({
      providers: [
        {
          name: 'powerschool',
          display_name: 'PowerSchool',
          description: 'PowerSchool Student Information System',
          supported_features: [
            'students', 'teachers', 'classes', 'enrollments', 
            'grades', 'attendance', 'schedules'
          ],
          authentication_type: 'oauth2',
          setup_complexity: 'medium',
          documentation_url: 'https://support.powerschool.com/developer',
        },
        {
          name: 'infinite_campus',
          display_name: 'Infinite Campus',
          description: 'Infinite Campus Student Information System',
          supported_features: [
            'students', 'teachers', 'classes', 'enrollments', 'grades'
          ],
          authentication_type: 'api_key',
          setup_complexity: 'high',
          documentation_url: 'https://kb.infinitecampus.com/api',
        },
        {
          name: 'skyward',
          display_name: 'Skyward',
          description: 'Skyward Student Management Suite',
          supported_features: [
            'students', 'teachers', 'classes', 'enrollments'
          ],
          authentication_type: 'basic_auth',
          setup_complexity: 'low',
          documentation_url: 'https://skyward.com/api-documentation',
        },
      ],
    });
  }),

  // Get field mapping options
  http.get('/api/sis/providers/:provider/fields', ({ params }) => {
    const fields = {
      powerschool: {
        student_fields: [
          { name: 'student_number', display: 'Student ID', required: true },
          { name: 'first_name', display: 'First Name', required: true },
          { name: 'last_name', display: 'Last Name', required: true },
          { name: 'email_addr', display: 'Email Address', required: false },
          { name: 'grade_level', display: 'Grade Level', required: true },
          { name: 'home_room', display: 'Home Room', required: false },
        ],
        teacher_fields: [
          { name: 'teacher_number', display: 'Teacher ID', required: true },
          { name: 'first_name', display: 'First Name', required: true },
          { name: 'last_name', display: 'Last Name', required: true },
          { name: 'email_addr', display: 'Email Address', required: true },
          { name: 'department', display: 'Department', required: false },
        ],
      },
    };
    
    return HttpResponse.json(fields[params.provider as keyof typeof fields] || {});
  }),
];

// Compliance API Mock Handlers
export const complianceHandlers = [
  // Get compliance dashboard
  http.get('/api/compliance/dashboard', ({ request }) => {
    const url = new URL(request.url);
    const tenant_id = url.searchParams.get('tenant_id');
    
    return HttpResponse.json({
      tenant_id: tenant_id || faker.string.uuid(),
      overall_score: faker.number.int({ min: 75, max: 98 }),
      compliance_frameworks: [
        {
          framework: 'COPPA',
          status: 'compliant',
          score: faker.number.int({ min: 85, max: 100 }),
          last_assessment: faker.date.recent().toISOString(),
          next_review: faker.date.future().toISOString(),
          findings: [],
        },
        {
          framework: 'FERPA',
          status: 'compliant',
          score: faker.number.int({ min: 85, max: 100 }),
          last_assessment: faker.date.recent().toISOString(),
          next_review: faker.date.future().toISOString(),
          findings: [],
        },
        {
          framework: 'GDPR',
          status: 'non_compliant',
          score: faker.number.int({ min: 60, max: 84 }),
          last_assessment: faker.date.recent().toISOString(),
          next_review: faker.date.soon().toISOString(),
          findings: [
            {
              severity: 'high',
              category: 'data_retention',
              description: 'Data retention policy exceeds maximum allowed period',
              remediation: 'Update retention policy to comply with GDPR requirements',
              due_date: faker.date.soon().toISOString(),
            }
          ],
        },
      ],
      recent_activities: Array.from({ length: 5 }, () => ({
        id: faker.string.uuid(),
        type: faker.helpers.arrayElement(['assessment', 'finding', 'remediation', 'policy_update']),
        description: faker.lorem.sentence(),
        framework: faker.helpers.arrayElement(['COPPA', 'FERPA', 'GDPR', 'CCPA']),
        timestamp: faker.date.recent().toISOString(),
        status: faker.helpers.arrayElement(['completed', 'in_progress', 'pending']),
      })),
      generated_at: new Date().toISOString(),
    });
  }),

  // Run compliance assessment
  http.post('/api/compliance/assessments', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      tenant_id: body.tenant_id,
      framework: body.framework,
      assessment_type: body.assessment_type || 'full',
      status: 'in_progress',
      progress: {
        current_stage: 'data_collection',
        total_stages: 6,
        completed_stages: 1,
        percentage: 16,
      },
      scope: {
        services: body.services || ['all'],
        data_types: body.data_types || ['all'],
        date_range: {
          start: body.date_range?.start || faker.date.past().toISOString(),
          end: body.date_range?.end || new Date().toISOString(),
        },
      },
      started_at: new Date().toISOString(),
      estimated_completion: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    }, { status: 201 });
  }),

  // Get assessment status
  http.get('/api/compliance/assessments/:assessmentId', ({ params }) => {
    const status = faker.helpers.arrayElement(['in_progress', 'completed', 'failed']);
    
    return HttpResponse.json({
      id: params.assessmentId,
      tenant_id: faker.string.uuid(),
      framework: 'GDPR',
      assessment_type: 'full',
      status,
      progress: {
        current_stage: status === 'completed' ? 'completed' : 'policy_review',
        total_stages: 6,
        completed_stages: status === 'completed' ? 6 : 4,
        percentage: status === 'completed' ? 100 : 66,
      },
      results: status === 'completed' ? {
        overall_score: faker.number.int({ min: 70, max: 95 }),
        status: faker.helpers.arrayElement(['compliant', 'non_compliant', 'partially_compliant']),
        findings: [
          {
            id: faker.string.uuid(),
            severity: 'medium',
            category: 'consent_management',
            rule: 'Article 7 - Conditions for consent',
            description: 'Consent records lack proper withdrawal mechanism tracking',
            evidence: ['Missing consent withdrawal timestamps in user records'],
            recommendation: 'Implement consent withdrawal tracking with timestamps',
            remediation_effort: 'medium',
            due_date: faker.date.future().toISOString(),
          }
        ],
        recommendations: [
          'Update privacy policy to include more specific data processing purposes',
          'Implement automated data retention policy enforcement',
          'Add consent withdrawal tracking mechanisms',
        ],
      } : undefined,
      started_at: faker.date.recent().toISOString(),
      completed_at: status === 'completed' ? faker.date.recent().toISOString() : null,
    });
  }),

  // Generate compliance report
  http.post('/api/compliance/reports', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      tenant_id: body.tenant_id,
      report_type: body.report_type,
      framework: body.framework,
      format: body.format || 'pdf',
      status: 'generating',
      progress: 0,
      parameters: {
        date_range: body.date_range,
        include_evidence: body.include_evidence || false,
        include_remediation: body.include_remediation || true,
      },
      requested_at: new Date().toISOString(),
      estimated_completion: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
    }, { status: 201 });
  }),

  // List compliance policies
  http.get('/api/compliance/policies', ({ request }) => {
    const url = new URL(request.url);
    const framework = url.searchParams.get('framework');
    
    const policies = Array.from({ length: 8 }, () => ({
      id: faker.string.uuid(),
      name: faker.lorem.words(3),
      framework: framework || faker.helpers.arrayElement(['COPPA', 'FERPA', 'GDPR', 'CCPA']),
      category: faker.helpers.arrayElement(['data_retention', 'consent_management', 'access_control', 'data_transfer']),
      status: faker.helpers.arrayElement(['active', 'draft', 'deprecated']),
      enforcement_level: faker.helpers.arrayElement(['mandatory', 'recommended', 'optional']),
      last_updated: faker.date.recent().toISOString(),
      next_review: faker.date.future().toISOString(),
      compliance_score: faker.number.int({ min: 70, max: 100 }),
    }));
    
    return HttpResponse.json({ policies });
  }),
];

// Health check handlers for additional services
export const additionalHealthHandlers = [
  http.get('/api/residency/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
    });
  }),

  http.get('/api/sis/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      active_connections: faker.number.int({ min: 1, max: 10 }),
      timestamp: new Date().toISOString(),
    });
  }),

  http.get('/api/compliance/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      frameworks_monitored: ['COPPA', 'FERPA', 'GDPR', 'CCPA'],
      timestamp: new Date().toISOString(),
    });
  }),
];
