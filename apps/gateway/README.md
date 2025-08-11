# @aivo/gateway

API Edge Gateway with Kong and Apollo Router for aivo-virtual-brains platform.

## 🏗️ Architecture

- **Kong Gateway**: Service mesh with declarative configuration
- **Apollo Router**: GraphQL federation layer
- **Custom Plugins**: Security, context, and compliance middleware

## 🔧 Services & Routes

### Kong Services

- `auth-svc` - Authentication and authorization service
- `user-svc` - User management service
- `apollo-router` - GraphQL federation endpoint
- `gateway-health` - Health check endpoint

### Security Features

- **JWT Authentication**: Validates tokens for protected routes
- **CORS**: Cross-origin resource sharing configuration
- **Rate Limiting**: Request throttling per consumer
- **Correlation ID**: Request tracing across services

### Custom Plugins

- `dash_context` - Dashboard context injection
- `learner_scope` - Learning scope validation
- `consent_gate` - Privacy consent enforcement

## 🚀 Development

```bash
# Start gateway stack
docker-compose up kong apollo-router

# Health check
curl http://localhost:8000/gateway/health
```

## 📋 API Endpoints

- `GET /gateway/health` - Gateway health status (200 OK)
- `POST /graphql` - GraphQL federation endpoint
- `GET|POST /auth/*` - Authentication service routes
- `GET|POST /users/*` - User service routes

## 🔒 Security

- Missing/invalid JWT → 401 Unauthorized
- Mismatched learner scope → 403 Forbidden
- Rate limiting per consumer
- CORS policy enforcement

## 🧪 Testing

The gateway can be tested using the provided test script or manually:

### Automated Testing

```powershell
# Run the comprehensive gateway test suite
.\test-gateway.ps1
```

### Manual Testing

```bash
# Test Kong Gateway health (expect 200)
curl http://localhost:8003/gateway/health

# Test Apollo Router GraphQL endpoint (expect GraphQL error response - indicates router is working)
curl http://localhost:4000/

# Test Kong Admin API
curl http://localhost:8001/status

# Test JWT authentication (expect 401 due to missing JWT)
curl http://localhost:8003/auth/profile

# Test CORS preflight
curl -X OPTIONS http://localhost:8003/graphql \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization,content-type"
```

### Expected Results

- ✅ Kong Gateway health endpoint returns 200 OK
- ✅ Apollo Router GraphQL endpoint is accessible (returns GraphQL error for invalid requests)
- ✅ JWT authentication properly rejects unauthenticated requests with 401
- ✅ CORS headers are properly configured for cross-origin requests
- ✅ Rate limiting is enforced for high-frequency requests
- ⚠️ Auth/User services return "name resolution failed" (expected - placeholder services)
