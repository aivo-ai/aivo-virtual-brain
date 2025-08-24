import { http, HttpResponse } from 'msw';
import { faker } from '@faker-js/faker';

// Chat API Mock Handlers
export const chatHandlers = [
  // List conversations
  http.get('/api/chat/conversations', ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '20');
    const offset = parseInt(url.searchParams.get('offset') || '0');
    const type = url.searchParams.get('type');

    const conversations = Array.from({ length: Math.min(limit, 10) }, (_, i) => ({
      id: faker.string.uuid(),
      type: type || faker.helpers.arrayElement(['direct', 'group', 'classroom', 'support']),
      title: faker.lorem.sentence(3),
      participant_ids: Array.from({ length: faker.number.int({ min: 2, max: 5 }) }, () => faker.string.uuid()),
      classroom_id: faker.string.uuid(),
      last_message: {
        id: faker.string.uuid(),
        content: faker.lorem.sentence(),
        sender_id: faker.string.uuid(),
        created_at: faker.date.recent().toISOString(),
      },
      unread_count: faker.number.int({ min: 0, max: 10 }),
      is_muted: faker.datatype.boolean(),
      is_ephemeral: faker.datatype.boolean(),
      created_at: faker.date.past().toISOString(),
      updated_at: faker.date.recent().toISOString(),
    }));

    return HttpResponse.json({
      conversations,
      total: 50,
      has_more: offset + limit < 50,
    });
  }),

  // Create conversation
  http.post('/api/chat/conversations', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      type: body.type,
      title: body.title,
      participant_ids: body.participant_ids || [],
      classroom_id: body.classroom_id,
      last_message: null,
      unread_count: 0,
      is_muted: false,
      is_ephemeral: body.is_ephemeral || false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Get messages in conversation
  http.get('/api/chat/conversations/:conversationId/messages', ({ params, request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '50');
    
    const messages = Array.from({ length: Math.min(limit, 20) }, (_, i) => ({
      id: faker.string.uuid(),
      conversation_id: params.conversationId,
      sender_id: faker.string.uuid(),
      content: faker.lorem.paragraph(),
      message_type: faker.helpers.arrayElement(['text', 'image', 'file', 'system', 'ai_response']),
      reply_to_id: i > 0 && faker.datatype.boolean() ? faker.string.uuid() : null,
      attachments: faker.datatype.boolean() ? [{
        id: faker.string.uuid(),
        filename: faker.system.fileName(),
        file_size: faker.number.int({ min: 1000, max: 5000000 }),
        mime_type: faker.system.mimeType(),
        url: faker.internet.url(),
        is_image: faker.datatype.boolean(),
        created_at: faker.date.recent().toISOString(),
      }] : [],
      reactions: [],
      is_edited: faker.datatype.boolean(),
      is_deleted: false,
      metadata: {},
      created_at: faker.date.recent().toISOString(),
      updated_at: faker.date.recent().toISOString(),
    }));

    return HttpResponse.json({
      messages,
      has_more: faker.datatype.boolean(),
    });
  }),

  // Send message
  http.post('/api/chat/conversations/:conversationId/messages', async ({ params, request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      conversation_id: params.conversationId,
      sender_id: faker.string.uuid(),
      content: body.content,
      message_type: body.message_type || 'text',
      reply_to_id: body.reply_to_id || null,
      attachments: body.attachments || [],
      reactions: [],
      is_edited: false,
      is_deleted: false,
      metadata: body.metadata || {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Upload file
  http.post('/api/chat/upload', async ({ request }) => {
    // Simulate file upload processing
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      filename: faker.system.fileName(),
      file_size: faker.number.int({ min: 1000, max: 10000000 }),
      mime_type: faker.system.mimeType(),
      url: faker.internet.url(),
      thumbnail_url: faker.datatype.boolean() ? faker.internet.url() : null,
      is_image: faker.datatype.boolean(),
      created_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Mark as read
  http.post('/api/chat/conversations/:conversationId/read', async ({ request }) => {
    return HttpResponse.json({
      success: true,
    });
  }),

  // Get/edit/delete specific message
  http.get('/api/chat/messages/:messageId', ({ params }) => {
    return HttpResponse.json({
      id: params.messageId,
      conversation_id: faker.string.uuid(),
      sender_id: faker.string.uuid(),
      content: faker.lorem.paragraph(),
      message_type: 'text',
      reply_to_id: null,
      attachments: [],
      reactions: [],
      is_edited: false,
      is_deleted: false,
      metadata: {},
      created_at: faker.date.recent().toISOString(),
      updated_at: faker.date.recent().toISOString(),
    });
  }),

  http.put('/api/chat/messages/:messageId', async ({ params, request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: params.messageId,
      conversation_id: faker.string.uuid(),
      sender_id: faker.string.uuid(),
      content: body.content,
      message_type: 'text',
      reply_to_id: null,
      attachments: [],
      reactions: [],
      is_edited: true,
      is_deleted: false,
      metadata: {},
      created_at: faker.date.past().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }),

  http.delete('/api/chat/messages/:messageId', ({ params }) => {
    return new HttpResponse(null, { status: 204 });
  }),
];

// SCIM API Mock Handlers
export const scimHandlers = [
  // List users
  http.get('/scim/v2/Users', ({ request }) => {
    const url = new URL(request.url);
    const count = parseInt(url.searchParams.get('count') || '20');
    const startIndex = parseInt(url.searchParams.get('startIndex') || '1');
    const filter = url.searchParams.get('filter');

    const users = Array.from({ length: Math.min(count, 10) }, (_, i) => ({
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      id: faker.string.uuid(),
      externalId: faker.string.alphanumeric(10),
      userName: faker.internet.email(),
      displayName: faker.person.fullName(),
      name: {
        formatted: faker.person.fullName(),
        familyName: faker.person.lastName(),
        givenName: faker.person.firstName(),
        middleName: faker.person.middleName(),
      },
      emails: [{
        value: faker.internet.email(),
        type: 'work',
        primary: true,
      }],
      active: faker.datatype.boolean(),
      groups: [],
      roles: [{
        value: faker.helpers.arrayElement(['teacher', 'student', 'admin']),
        display: faker.helpers.arrayElement(['Teacher', 'Student', 'Administrator']),
        primary: true,
      }],
      meta: {
        resourceType: 'User',
        created: faker.date.past().toISOString(),
        lastModified: faker.date.recent().toISOString(),
        location: `/scim/v2/Users/${faker.string.uuid()}`,
        version: 'W/"1"',
      },
    }));

    return HttpResponse.json({
      schemas: ['urn:ietf:params:scim:api:messages:2.0:ListResponse'],
      totalResults: 100,
      startIndex,
      itemsPerPage: users.length,
      Resources: users,
    });
  }),

  // Create user
  http.post('/scim/v2/Users', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      id: faker.string.uuid(),
      externalId: body.externalId,
      userName: body.userName,
      displayName: body.displayName || body.name?.formatted,
      name: body.name,
      emails: body.emails,
      active: body.active !== false,
      groups: [],
      roles: body.roles || [],
      meta: {
        resourceType: 'User',
        created: new Date().toISOString(),
        lastModified: new Date().toISOString(),
        location: `/scim/v2/Users/${faker.string.uuid()}`,
        version: 'W/"1"',
      },
    }, { status: 201 });
  }),

  // Get user
  http.get('/scim/v2/Users/:id', ({ params }) => {
    return HttpResponse.json({
      schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
      id: params.id,
      externalId: faker.string.alphanumeric(10),
      userName: faker.internet.email(),
      displayName: faker.person.fullName(),
      name: {
        formatted: faker.person.fullName(),
        familyName: faker.person.lastName(),
        givenName: faker.person.firstName(),
      },
      emails: [{
        value: faker.internet.email(),
        type: 'work',
        primary: true,
      }],
      active: true,
      groups: [],
      roles: [],
      meta: {
        resourceType: 'User',
        created: faker.date.past().toISOString(),
        lastModified: faker.date.recent().toISOString(),
        location: `/scim/v2/Users/${params.id}`,
        version: 'W/"1"',
      },
    });
  }),

  // Update user
  http.put('/scim/v2/Users/:id', async ({ params, request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      ...body,
      id: params.id,
      meta: {
        resourceType: 'User',
        created: faker.date.past().toISOString(),
        lastModified: new Date().toISOString(),
        location: `/scim/v2/Users/${params.id}`,
        version: 'W/"2"',
      },
    });
  }),

  // Delete user
  http.delete('/scim/v2/Users/:id', ({ params }) => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Bulk operations
  http.post('/scim/v2/Bulk', async ({ request }) => {
    const body = await request.json() as any;
    
    const operations = body.Operations.map((op: any) => ({
      bulkId: op.bulkId,
      method: op.method,
      location: op.method === 'POST' ? `/scim/v2/Users/${faker.string.uuid()}` : undefined,
      status: '201',
      response: op.method === 'POST' ? {
        schemas: ['urn:ietf:params:scim:schemas:core:2.0:User'],
        id: faker.string.uuid(),
        userName: op.data?.userName || faker.internet.email(),
        displayName: op.data?.displayName || faker.person.fullName(),
        active: true,
        meta: {
          resourceType: 'User',
          created: new Date().toISOString(),
          lastModified: new Date().toISOString(),
          version: 'W/"1"',
        },
      } : undefined,
    }));

    return HttpResponse.json({
      schemas: ['urn:ietf:params:scim:api:messages:2.0:BulkResponse'],
      Operations: operations,
    });
  }),
];

// Verification API Mock Handlers
export const verificationHandlers = [
  // Start verification
  http.post('/api/verify/sessions', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      user_id: body.user_id,
      verification_type: body.verification_type,
      status: 'pending',
      provider: body.preferred_provider || 'idme',
      provider_session_id: faker.string.alphanumeric(16),
      verification_url: faker.internet.url(),
      required_documents: body.required_documents || ['drivers_license'],
      uploaded_documents: [],
      progress: {
        current_step: 'document_upload',
        total_steps: 4,
        completed_steps: 0,
      },
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Get verification status
  http.get('/api/verify/sessions/:sessionId', ({ params }) => {
    const status = faker.helpers.arrayElement(['pending', 'document_upload', 'selfie_required', 'processing', 'completed', 'failed']);
    
    return HttpResponse.json({
      id: params.sessionId,
      user_id: faker.string.uuid(),
      verification_type: 'guardian',
      status,
      provider: 'idme',
      provider_session_id: faker.string.alphanumeric(16),
      verification_url: faker.internet.url(),
      required_documents: ['drivers_license'],
      uploaded_documents: status !== 'pending' ? [{
        document_type: 'drivers_license',
        side: 'front',
        status: 'verified',
        uploaded_at: faker.date.recent().toISOString(),
      }] : [],
      progress: {
        current_step: status,
        total_steps: 4,
        completed_steps: status === 'completed' ? 4 : 2,
      },
      result: status === 'completed' ? {
        status: 'completed',
        decision: 'approved',
        confidence_score: 0.95,
        verification_level: 'high',
        verified_attributes: {
          identity_verified: true,
          age_verified: true,
          address_verified: true,
          document_authentic: true,
          biometric_match: true,
        },
        completed_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
      } : undefined,
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      created_at: faker.date.past().toISOString(),
      updated_at: faker.date.recent().toISOString(),
    });
  }),

  // Upload document
  http.post('/api/verify/sessions/:sessionId/documents', async ({ params, request }) => {
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      document_type: 'drivers_license',
      side: 'front',
      status: 'processing',
      file_url: faker.internet.url(),
      extracted_data: {
        name: faker.person.fullName(),
        date_of_birth: faker.date.birthdate().toISOString().split('T')[0],
        document_number: faker.string.alphanumeric(12),
        expiration_date: faker.date.future().toISOString().split('T')[0],
        issuing_state: faker.location.state({ abbreviated: true }),
        address: {
          street: faker.location.streetAddress(),
          city: faker.location.city(),
          state: faker.location.state({ abbreviated: true }),
          zip_code: faker.location.zipCode(),
        },
      },
      confidence_score: faker.number.float({ min: 0.8, max: 1.0 }),
      uploaded_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Upload selfie
  http.post('/api/verify/sessions/:sessionId/selfie', async ({ params, request }) => {
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      status: 'processing',
      file_url: faker.internet.url(),
      liveness_score: faker.number.float({ min: 0.85, max: 1.0 }),
      face_match_score: faker.number.float({ min: 0.85, max: 1.0 }),
      uploaded_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Submit verification
  http.post('/api/verify/sessions/:sessionId/submit', async ({ params }) => {
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    return HttpResponse.json({
      status: 'completed',
      decision: faker.helpers.arrayElement(['approved', 'rejected', 'pending_review']),
      confidence_score: faker.number.float({ min: 0.7, max: 1.0 }),
      verification_level: faker.helpers.arrayElement(['low', 'medium', 'high', 'verified']),
      verified_attributes: {
        identity_verified: true,
        age_verified: true,
        address_verified: faker.datatype.boolean(),
        document_authentic: true,
        biometric_match: true,
      },
      completed_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    });
  }),

  // List providers
  http.get('/api/verify/providers', () => {
    return HttpResponse.json({
      providers: [
        {
          name: 'idme',
          display_name: 'ID.me',
          supported_documents: ['drivers_license', 'passport', 'state_id'],
          features: {
            document_verification: true,
            biometric_matching: true,
            liveness_detection: true,
            real_time_processing: true,
          },
          availability: 'available',
          cost_per_verification: 2.50,
          average_processing_time: 30,
        },
        {
          name: 'jumio',
          display_name: 'Jumio',
          supported_documents: ['drivers_license', 'passport', 'state_id', 'government_id'],
          features: {
            document_verification: true,
            biometric_matching: true,
            liveness_detection: true,
            real_time_processing: true,
          },
          availability: 'available',
          cost_per_verification: 3.00,
          average_processing_time: 45,
        },
      ],
    });
  }),
];

// Tax API Mock Handlers
export const taxHandlers = [
  // Calculate tax
  http.post('/api/payments/tax/calculate', async ({ request }) => {
    const body = await request.json() as any;
    
    const subtotal = body.amount;
    const taxRate = 0.0875; // 8.75% example rate
    const totalTax = subtotal * taxRate;
    
    return HttpResponse.json({
      subtotal: subtotal,
      total_tax: parseFloat(totalTax.toFixed(2)),
      total_amount: parseFloat((subtotal + totalTax).toFixed(2)),
      currency: body.currency || 'USD',
      breakdown: [
        {
          jurisdiction: 'CA',
          jurisdiction_type: 'state',
          tax_type: 'sales',
          rate: 0.06,
          amount: parseFloat((subtotal * 0.06).toFixed(2)),
          taxable_amount: subtotal,
        },
        {
          jurisdiction: 'Los Angeles County',
          jurisdiction_type: 'county',
          tax_type: 'sales',
          rate: 0.0275,
          amount: parseFloat((subtotal * 0.0275).toFixed(2)),
          taxable_amount: subtotal,
        },
      ],
      calculation_id: faker.string.uuid(),
      calculated_at: new Date().toISOString(),
    });
  }),

  // Get tax rates
  http.get('/api/payments/tax/rates', ({ request }) => {
    const url = new URL(request.url);
    const jurisdiction = url.searchParams.get('jurisdiction') || 'US-CA';
    
    return HttpResponse.json({
      jurisdiction,
      rates: [
        {
          type: 'state_sales',
          rate: 0.06,
          minimum_threshold: 0,
        },
        {
          type: 'county_sales',
          rate: 0.0275,
          minimum_threshold: 0,
        },
        {
          type: 'city_sales',
          rate: 0.01,
          minimum_threshold: 0,
        },
      ],
      effective_date: '2024-01-01',
      next_update: '2025-01-01',
    });
  }),

  // List jurisdictions
  http.get('/api/payments/tax/jurisdictions', () => {
    return HttpResponse.json({
      jurisdictions: [
        {
          code: 'US-CA',
          name: 'California',
          type: 'state',
          country: 'US',
          supported_taxes: ['sales', 'use'],
        },
        {
          code: 'US-NY',
          name: 'New York',
          type: 'state',
          country: 'US',
          supported_taxes: ['sales', 'use'],
        },
        {
          code: 'CA-ON',
          name: 'Ontario',
          type: 'province',
          country: 'CA',
          supported_taxes: ['hst'],
        },
      ],
    });
  }),
];

// Legal Hold API Mock Handlers
export const legalHoldHandlers = [
  // List legal holds
  http.get('/api/legal-holds', ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    
    const holds = Array.from({ length: 5 }, () => ({
      id: faker.string.uuid(),
      hold_number: `LH-${faker.string.numeric(6)}`,
      title: faker.lorem.sentence(4),
      description: faker.lorem.paragraph(),
      case_number: `CASE-${new Date().getFullYear()}-${faker.string.numeric(3)}`,
      legal_basis: faker.helpers.arrayElement(['litigation', 'investigation', 'regulatory', 'compliance']),
      status: status || faker.helpers.arrayElement(['active', 'released', 'expired', 'suspended']),
      scope_type: faker.helpers.arrayElement(['tenant', 'learner', 'teacher', 'classroom', 'timerange']),
      scope_parameters: {
        tenant_id: faker.string.uuid(),
      },
      effective_date: faker.date.past().toISOString(),
      expiration_date: faker.date.future().toISOString(),
      created_at: faker.date.past().toISOString(),
      affected_entities_count: faker.number.int({ min: 10, max: 1000 }),
      custodians_count: faker.number.int({ min: 1, max: 10 }),
    }));
    
    return HttpResponse.json({ holds });
  }),

  // Create legal hold
  http.post('/api/legal-holds', async ({ request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      hold_number: `LH-${faker.string.numeric(6)}`,
      title: body.title,
      description: body.description,
      case_number: body.case_number,
      legal_basis: body.legal_basis,
      status: 'active',
      scope_type: body.scope_type,
      scope_parameters: body.scope_parameters,
      effective_date: new Date().toISOString(),
      expiration_date: null,
      created_at: new Date().toISOString(),
      affected_entities_count: 0,
      custodians_count: body.custodian_user_ids?.length || 0,
    }, { status: 201 });
  }),

  // Get legal hold
  http.get('/api/legal-holds/:holdId', ({ params }) => {
    return HttpResponse.json({
      id: params.holdId,
      hold_number: `LH-${faker.string.numeric(6)}`,
      title: faker.lorem.sentence(4),
      description: faker.lorem.paragraph(),
      case_number: `CASE-${new Date().getFullYear()}-${faker.string.numeric(3)}`,
      legal_basis: 'litigation',
      status: 'active',
      scope_type: 'tenant',
      scope_parameters: {
        tenant_id: faker.string.uuid(),
      },
      effective_date: faker.date.past().toISOString(),
      created_at: faker.date.past().toISOString(),
      affected_entities_count: faker.number.int({ min: 100, max: 1000 }),
      custodians_count: faker.number.int({ min: 3, max: 8 }),
    });
  }),

  // Create eDiscovery export
  http.post('/api/ediscovery/:holdId/exports', async ({ params, request }) => {
    const body = await request.json() as any;
    
    return HttpResponse.json({
      id: faker.string.uuid(),
      export_number: `EXP-${faker.string.numeric(6)}`,
      title: body.title,
      status: 'pending',
      progress_percentage: 0,
      total_records: 0,
      exported_records: 0,
      file_count: 0,
      total_size_bytes: 0,
      requested_date: new Date().toISOString(),
      archive_location: null,
    }, { status: 201 });
  }),

  // List exports
  http.get('/api/ediscovery/:holdId/exports', ({ params }) => {
    const exports = Array.from({ length: 3 }, () => ({
      id: faker.string.uuid(),
      export_number: `EXP-${faker.string.numeric(6)}`,
      title: faker.lorem.sentence(3),
      status: faker.helpers.arrayElement(['pending', 'in_progress', 'completed', 'failed']),
      progress_percentage: faker.number.int({ min: 0, max: 100 }),
      total_records: faker.number.int({ min: 1000, max: 10000 }),
      exported_records: faker.number.int({ min: 500, max: 10000 }),
      file_count: faker.number.int({ min: 10, max: 100 }),
      total_size_bytes: faker.number.int({ min: 1000000, max: 1000000000 }),
      requested_date: faker.date.past().toISOString(),
      completed_date: faker.datatype.boolean() ? faker.date.recent().toISOString() : null,
      archive_location: faker.datatype.boolean() ? faker.internet.url() : null,
    }));
    
    return HttpResponse.json({ exports });
  }),
];

// Health check handlers
export const healthHandlers = [
  http.get('/api/chat/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
    });
  }),

  http.get('/api/verify/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      providers: {
        idme: 'available',
        jumio: 'available',
        onfido: 'available',
      },
    });
  }),

  http.get('/api/legal-holds/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
    });
  }),
];
