-- AIVO Virtual Brains - Dash Context Plugin
-- S1-09 Implementation
-- Injects dashboard context headers and validates request context
local kong = kong
local type = type
local pairs = pairs

local DashContextHandler = {}

DashContextHandler.PRIORITY = 1000
DashContextHandler.VERSION = "1.0.0"

-- Schema for plugin configuration
local schema = {
  name = "dash_context",
  fields = {
    { config = {
        type = "record",
        fields = {
          { header_prefix = { type = "string", default = "X-Dash-" } },
          { context_header = { type = "string", default = "X-Dashboard-Context" } },
          { user_id_header = { type = "string", default = "X-User-ID" } },
          { tenant_id_header = { type = "string", default = "X-Tenant-ID" } },
          { required_context = { type = "boolean", default = true } },
          { allowed_contexts = { 
              type = "array", 
              elements = { type = "string" }, 
              default = { "learner", "teacher", "guardian", "admin" }
          }},
        }
    }}
  }
}

-- Extract JWT claims for context
local function extract_jwt_claims(jwt_token)
  if not jwt_token or jwt_token == "" then
    return nil
  end
  
  -- Remove "Bearer " prefix if present
  jwt_token = jwt_token:match("Bearer%s+(.+)") or jwt_token
  
  -- For demo purposes, we'll decode a simple JWT structure
  -- In production, use proper JWT validation library
  local jwt = require "resty.jwt"
  local jwt_obj = jwt:verify("your-secret-key", jwt_token)
  
  if jwt_obj and jwt_obj.valid then
    return jwt_obj.payload
  end
  
  return nil
end

-- Validate dashboard context
local function validate_context(context, allowed_contexts)
  if not context then
    return false, "Missing dashboard context"
  end
  
  for _, allowed in ipairs(allowed_contexts) do
    if context == allowed then
      return true
    end
  end
  
  return false, "Invalid dashboard context: " .. context
end

-- Main access phase handler
function DashContextHandler:access(conf)
  kong.log.debug("DashContext plugin: Starting access phase")
  
  -- Get request headers
  local headers = kong.request.get_headers()
  local auth_header = headers["authorization"]
  local context_header = headers[conf.context_header:lower()]
  
  -- Extract user information from JWT
  local jwt_claims = extract_jwt_claims(auth_header)
  if not jwt_claims then
    if conf.required_context then
      kong.log.warn("DashContext plugin: No valid JWT found")
      return kong.response.exit(401, { 
        message = "Unauthorized: Valid JWT required for dashboard context",
        code = "MISSING_JWT"
      })
    end
  end
  
  -- Validate dashboard context if provided
  if context_header then
    local valid, err = validate_context(context_header, conf.allowed_contexts)
    if not valid then
      kong.log.warn("DashContext plugin: Invalid context - " .. err)
      return kong.response.exit(403, { 
        message = err,
        code = "INVALID_CONTEXT"
      })
    end
  elseif conf.required_context then
    kong.log.warn("DashContext plugin: Missing required dashboard context")
    return kong.response.exit(400, { 
      message = "Missing required dashboard context header: " .. conf.context_header,
      code = "MISSING_CONTEXT"
    })
  end
  
  -- Inject context headers for downstream services
  if jwt_claims then
    -- Set user context headers
    if jwt_claims.sub then
      kong.service.request.set_header(conf.user_id_header, jwt_claims.sub)
    end
    
    if jwt_claims.tenant_id then
      kong.service.request.set_header(conf.tenant_id_header, jwt_claims.tenant_id)
    end
    
    -- Set learner context if present
    if jwt_claims.learner_uid then
      kong.service.request.set_header(conf.header_prefix .. "Learner-ID", jwt_claims.learner_uid)
    end
    
    -- Set role context
    if jwt_claims.role then
      kong.service.request.set_header(conf.header_prefix .. "User-Role", jwt_claims.role)
    end
  end
  
  -- Forward the dashboard context
  if context_header then
    kong.service.request.set_header(conf.header_prefix .. "Context", context_header)
  end
  
  -- Add correlation metadata
  local correlation_id = headers["x-correlation-id"] or kong.tools.uuid.uuid()
  kong.service.request.set_header("X-Correlation-ID", correlation_id)
  kong.service.request.set_header(conf.header_prefix .. "Timestamp", os.time())
  
  kong.log.info("DashContext plugin: Context validated and headers injected")
end

-- Response header phase - add context info to response
function DashContextHandler:header_filter(conf)
  -- Add context information to response headers for debugging
  local context = kong.service.request.get_header(conf.header_prefix .. "Context")
  if context then
    kong.response.set_header("X-Dashboard-Context-Applied", context)
  end
  
  kong.response.set_header("X-Plugin-DashContext", "1.0.0")
end

return {
  [schema.name] = schema,
  DashContextHandler
}
