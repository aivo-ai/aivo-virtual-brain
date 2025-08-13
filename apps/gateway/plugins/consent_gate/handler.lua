-- AIVO Virtual Brains - Consent Gate Plugin
-- S1-09 Implementation  
-- Enforces privacy consent requirements with Redis cache
local kong = kong
local redis = require "resty.redis"

local ConsentGateHandler = {}

ConsentGateHandler.PRIORITY = 900
ConsentGateHandler.VERSION = "1.0.0"

-- Schema for plugin configuration
local schema = {
  name = "consent_gate",
  fields = {
    { config = {
        type = "record",
        fields = {
          { redis_host = { type = "string", default = "redis" } },
          { redis_port = { type = "number", default = 6379 } },
          { redis_timeout = { type = "number", default = 1000 } },
          { redis_password = { type = "string" } },
          { redis_database = { type = "number", default = 0 } },
          { consent_key_prefix = { type = "string", default = "consent:" } },
          { cache_ttl = { type = "number", default = 3600 } }, -- 1 hour
          { require_consent_for_paths = { 
              type = "array", 
              elements = { type = "string" }, 
              default = { "/learners/", "/persona/", "/private-brain/" }
          }},
          { bypass_roles = { 
              type = "array", 
              elements = { type = "string" }, 
              default = { "admin" }
          }},
          { enforce_consent = { type = "boolean", default = true } },
          { default_consent_status = { type = "boolean", default = false } }
        }
    }}
  }
}

-- Create Redis connection
local function create_redis_connection(conf)
  local red = redis:new()
  red:set_timeout(conf.redis_timeout)
  
  local ok, err = red:connect(conf.redis_host, conf.redis_port)
  if not ok then
    kong.log.err("ConsentGate plugin: Failed to connect to Redis: ", err)
    return nil, err
  end
  
  -- Authenticate if password is provided
  if conf.redis_password and conf.redis_password ~= "" then
    local res, err = red:auth(conf.redis_password)
    if not res then
      kong.log.err("ConsentGate plugin: Redis authentication failed: ", err)
      red:close()
      return nil, err
    end
  end
  
  -- Select database
  if conf.redis_database and conf.redis_database > 0 then
    local res, err = red:select(conf.redis_database)
    if not res then
      kong.log.err("ConsentGate plugin: Redis database selection failed: ", err)
      red:close()
      return nil, err
    end
  end
  
  return red, nil
end

-- Check if path requires consent
local function requires_consent(path, consent_paths)
  for _, consent_path in ipairs(consent_paths) do
    if string.find(path, consent_path, 1, true) then
      return true
    end
  end
  return false
end

-- Extract learner ID from JWT claims
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

-- Get consent status from Redis cache
local function get_consent_status(red, learner_id, conf)
  local consent_key = conf.consent_key_prefix .. learner_id
  
  local consent_data, err = red:get(consent_key)
  if err then
    kong.log.err("ConsentGate plugin: Redis GET error: ", err)
    return nil, err
  end
  
  if consent_data == ngx.null then
    kong.log.debug("ConsentGate plugin: No consent data found for learner: " .. learner_id)
    return nil, "no_consent_data"
  end
  
  -- Parse JSON consent data
  local cjson = require "cjson"
  local ok, consent_obj = pcall(cjson.decode, consent_data)
  if not ok then
    kong.log.err("ConsentGate plugin: Failed to parse consent data: ", consent_obj)
    return nil, "invalid_consent_format"
  end
  
  return consent_obj, nil
end

-- Cache consent status in Redis
local function cache_consent_status(red, learner_id, consent_status, conf)
  local consent_key = conf.consent_key_prefix .. learner_id
  local cjson = require "cjson"
  
  local consent_data = cjson.encode({
    status = consent_status,
    timestamp = os.time(),
    cached = true
  })
  
  local ok, err = red:setex(consent_key, conf.cache_ttl, consent_data)
  if not ok then
    kong.log.err("ConsentGate plugin: Failed to cache consent status: ", err)
  end
  
  return ok, err
end

-- Check if user role can bypass consent enforcement
local function can_bypass_consent(user_role, bypass_roles)
  if not user_role or not bypass_roles then
    return false
  end
  
  for _, role in ipairs(bypass_roles) do
    if user_role == role then
      kong.log.debug("ConsentGate plugin: User role '" .. user_role .. "' can bypass consent")
      return true
    end
  end
  
  return false
end

-- Main access phase handler
function ConsentGateHandler:access(conf)
  kong.log.debug("ConsentGate plugin: Starting access phase")
  
  if not conf.enforce_consent then
    kong.log.debug("ConsentGate plugin: Consent enforcement disabled")
    return
  end
  
  -- Get current request path
  local path = kong.request.get_path()
  
  -- Check if this path requires consent
  if not requires_consent(path, conf.require_consent_for_paths) then
    kong.log.debug("ConsentGate plugin: Path does not require consent: " .. path)
    return
  end
  
  -- Get JWT from authorization header
  local headers = kong.request.get_headers()
  local auth_header = headers["authorization"]
  
  if not auth_header then
    kong.log.warn("ConsentGate plugin: No authorization header found")
    return kong.response.exit(401, { 
      message = "Unauthorized: JWT required for consent validation",
      code = "MISSING_JWT"
    })
  end
  
  -- Extract JWT claims
  local jwt_claims = extract_jwt_claims(auth_header)
  if not jwt_claims then
    kong.log.warn("ConsentGate plugin: Invalid or expired JWT")
    return kong.response.exit(401, { 
      message = "Unauthorized: Invalid JWT token",
      code = "INVALID_JWT"
    })
  end
  
  -- Check if user role can bypass consent enforcement
  if can_bypass_consent(jwt_claims.role, conf.bypass_roles) then
    kong.log.info("ConsentGate plugin: User with role '" .. (jwt_claims.role or "unknown") .. "' bypassing consent check")
    return
  end
  
  -- Get learner ID for consent check
  local learner_id = jwt_claims.learner_uid or jwt_claims.sub
  if not learner_id then
    kong.log.warn("ConsentGate plugin: No learner ID found in JWT")
    return kong.response.exit(403, { 
      message = "Forbidden: No learner identifier in JWT",
      code = "NO_LEARNER_ID"
    })
  end
  
  -- Connect to Redis
  local red, err = create_redis_connection(conf)
  if not red then
    kong.log.err("ConsentGate plugin: Redis connection failed: ", err)
    -- Fallback to default consent status
    if not conf.default_consent_status then
      return kong.response.exit(503, { 
        message = "Service temporarily unavailable: Consent service error",
        code = "CONSENT_SERVICE_ERROR"
      })
    else
      kong.log.warn("ConsentGate plugin: Using default consent status due to Redis error")
    end
  else
    -- Get consent status from Redis
    local consent_obj, err = get_consent_status(red, learner_id, conf)
    
    if err and err ~= "no_consent_data" then
      kong.log.err("ConsentGate plugin: Error getting consent status: ", err)
      red:close()
      
      if not conf.default_consent_status then
        return kong.response.exit(503, { 
          message = "Service temporarily unavailable: Consent validation error",
          code = "CONSENT_VALIDATION_ERROR"
        })
      end
    elseif not consent_obj then
      -- No consent data found, use default
      kong.log.debug("ConsentGate plugin: No consent data, using default status")
      if not conf.default_consent_status then
        red:close()
        return kong.response.exit(451, { 
          message = "Consent required: No consent record found for this learner",
          code = "CONSENT_NOT_FOUND"
        })
      end
    else
      -- Check consent status
      if not consent_obj.status then
        red:close()
        return kong.response.exit(451, { 
          message = "Consent required: Privacy consent has not been granted",
          code = "CONSENT_DENIED",
          details = {
            learner_id = learner_id,
            consent_timestamp = consent_obj.timestamp
          }
        })
      end
      
      kong.log.info("ConsentGate plugin: Consent validated for learner: " .. learner_id)
    end
    
    red:close()
  end
  
  -- Set consent validation headers for downstream services
  kong.service.request.set_header("X-Consent-Validated", "true")
  kong.service.request.set_header("X-Consent-Learner-ID", learner_id)
  kong.service.request.set_header("X-Consent-Timestamp", os.time())
end

-- Response header phase
function ConsentGateHandler:header_filter(conf)
  -- Add plugin version to response headers for debugging
  kong.response.set_header("X-Plugin-ConsentGate", "1.0.0")
  
  -- Add consent validation status if it was performed
  local validated = kong.service.request.get_header("X-Consent-Validated")
  if validated then
    kong.response.set_header("X-Consent-Status", "validated")
  end
end

return {
  [schema.name] = schema,
  ConsentGateHandler
}
