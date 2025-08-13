-- AIVO Virtual Brains - Learner Scope Plugin
-- S1-09 Implementation
-- Enforces learner ID path parameter matches JWT learner_uid claim
local kong = kong
local string_find = string.find
local string_match = string.match

local LearnerScopeHandler = {}

LearnerScopeHandler.PRIORITY = 950
LearnerScopeHandler.VERSION = "1.0.0"

-- Schema for plugin configuration
local schema = {
  name = "learner_scope",
  fields = {
    { config = {
        type = "record",
        fields = {
          { learner_param_name = { type = "string", default = "learnerId" } },
          { jwt_learner_claim = { type = "string", default = "learner_uid" } },
          { bypass_roles = { 
              type = "array", 
              elements = { type = "string" }, 
              default = { "admin", "teacher" }
          }},
          { enforce_scope = { type = "boolean", default = true } },
          { error_response = { 
              type = "record",
              fields = {
                { status = { type = "number", default = 403 } },
                { message = { type = "string", default = "Learner scope violation: Access denied" } },
                { code = { type = "string", default = "LEARNER_SCOPE_VIOLATION" } }
              }
          }}
        }
    }}
  }
}

-- Extract learner ID from path parameters
local function extract_learner_id_from_path(path, param_name)
  -- Match patterns like /learners/{learnerId}/ or /api/learners/{learnerId}/persona
  local patterns = {
    "/learners/([^/]+)",
    "/api/learners/([^/]+)",
    "/" .. param_name .. "/([^/]+)",
    "/.*/" .. param_name .. "/([^/]+)"
  }
  
  for _, pattern in ipairs(patterns) do
    local learner_id = string_match(path, pattern)
    if learner_id then
      kong.log.debug("LearnerScope plugin: Extracted learner ID from path: " .. learner_id)
      return learner_id
    end
  end
  
  return nil
end

-- Extract JWT claims for learner validation
local function extract_jwt_claims(jwt_token)
  if not jwt_token or jwt_token == "" then
    return nil
  end
  
  -- Remove "Bearer " prefix if present
  jwt_token = jwt_token:match("Bearer%s+(.+)") or jwt_token
  
  -- For demo purposes, simplified JWT parsing
  -- In production, use proper JWT validation library
  local jwt = require "resty.jwt"
  local jwt_obj = jwt:verify("your-secret-key", jwt_token)
  
  if jwt_obj and jwt_obj.valid then
    return jwt_obj.payload
  end
  
  return nil
end

-- Check if user role can bypass learner scope enforcement
local function can_bypass_scope(user_role, bypass_roles)
  if not user_role or not bypass_roles then
    return false
  end
  
  for _, role in ipairs(bypass_roles) do
    if user_role == role then
      kong.log.debug("LearnerScope plugin: User role '" .. user_role .. "' can bypass scope")
      return true
    end
  end
  
  return false
end

-- Main access phase handler
function LearnerScopeHandler:access(conf)
  kong.log.debug("LearnerScope plugin: Starting access phase")
  
  if not conf.enforce_scope then
    kong.log.debug("LearnerScope plugin: Scope enforcement disabled")
    return
  end
  
  -- Get current request path
  local path = kong.request.get_path()
  kong.log.debug("LearnerScope plugin: Checking path: " .. path)
  
  -- Extract learner ID from path
  local path_learner_id = extract_learner_id_from_path(path, conf.learner_param_name)
  
  if not path_learner_id then
    kong.log.debug("LearnerScope plugin: No learner ID found in path, skipping validation")
    return
  end
  
  -- Get JWT from authorization header
  local headers = kong.request.get_headers()
  local auth_header = headers["authorization"]
  
  if not auth_header then
    kong.log.warn("LearnerScope plugin: No authorization header found")
    return kong.response.exit(401, { 
      message = "Unauthorized: JWT required for learner scope validation",
      code = "MISSING_JWT"
    })
  end
  
  -- Extract JWT claims
  local jwt_claims = extract_jwt_claims(auth_header)
  if not jwt_claims then
    kong.log.warn("LearnerScope plugin: Invalid or expired JWT")
    return kong.response.exit(401, { 
      message = "Unauthorized: Invalid JWT token",
      code = "INVALID_JWT"
    })
  end
  
  -- Check if user role can bypass scope enforcement
  if can_bypass_scope(jwt_claims.role, conf.bypass_roles) then
    kong.log.info("LearnerScope plugin: User with role '" .. (jwt_claims.role or "unknown") .. "' bypassing scope check")
    return
  end
  
  -- Get learner ID from JWT claims
  local jwt_learner_id = jwt_claims[conf.jwt_learner_claim]
  
  if not jwt_learner_id then
    kong.log.warn("LearnerScope plugin: No learner_uid claim found in JWT")
    return kong.response.exit(403, { 
      message = "Forbidden: No learner scope in JWT token",
      code = "NO_LEARNER_SCOPE"
    })
  end
  
  -- Validate that path learner ID matches JWT learner ID
  if path_learner_id ~= jwt_learner_id then
    kong.log.warn(string.format(
      "LearnerScope plugin: Scope violation - Path learner ID '%s' does not match JWT learner ID '%s'",
      path_learner_id, jwt_learner_id
    ))
    
    return kong.response.exit(conf.error_response.status, { 
      message = conf.error_response.message,
      code = conf.error_response.code,
      details = {
        path_learner_id = path_learner_id,
        jwt_learner_id = jwt_learner_id
      }
    })
  end
  
  kong.log.info("LearnerScope plugin: Learner scope validation successful for learner: " .. jwt_learner_id)
  
  -- Set validated learner ID in request headers for downstream services
  kong.service.request.set_header("X-Validated-Learner-ID", jwt_learner_id)
  kong.service.request.set_header("X-Learner-Scope-Validated", "true")
end

-- Response header phase
function LearnerScopeHandler:header_filter(conf)
  -- Add plugin version to response headers for debugging
  kong.response.set_header("X-Plugin-LearnerScope", "1.0.0")
  
  -- Add scope validation status if it was performed
  local validated = kong.service.request.get_header("X-Learner-Scope-Validated")
  if validated then
    kong.response.set_header("X-Learner-Scope-Status", "validated")
  end
end

return {
  [schema.name] = schema,
  LearnerScopeHandler
}
