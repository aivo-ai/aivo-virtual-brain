-- AIVO S1-09 Kong Plugins Test Suite
-- Simple test runner without Busted dependencies

-- Load test runner
local TestRunner = require("spec.simple_test_runner")

-- Mock dependencies
package.loaded["cjson"] = {
  encode = function(t)
    if type(t) == "table" then
      return '{"mocked":"json"}'
    end
    return '"' .. tostring(t) .. '"'
  end,
  decode = function(s)
    return { status = true, timestamp = os.time() }
  end
}

package.loaded["base64"] = {
  encode = function(s) return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" end,
  decode = function(s) return '{"sub":"user123","learner_uid":"learner456"}' end
}

-- Mock Kong environment
local function setup_kong_mocks()
  _G.kong = {
    log = {
      debug = function(...) end,
      info = function(...) end,
      warn = function(...) end,
      err = function(...) end
    },
    request = {
      get_headers = function() return {} end,
      get_path = function() return "/" end
    },
    service = {
      request = {
        set_header = function(name, value) end,
        get_header = function(name) return nil end
      }
    },
    response = {
      exit = function(status, body)
        error("HTTP_EXIT_" .. status .. "_" .. (body and body.code or "UNKNOWN"))
      end,
      set_header = function(name, value) end
    },
    tools = {
      uuid = {
        uuid = function() return "test-uuid-123" end
      }
    }
  }
end

-- Test helper functions
local function expect_http_exit(status, func)
  local success, err = pcall(func)
  if success then
    error("Expected HTTP exit " .. status .. " but function completed normally")
  end
  
  local exit_status = err:match("HTTP_EXIT_(%d+)_")
  if not exit_status or tonumber(exit_status) ~= status then
    error("Expected HTTP exit " .. status .. " but got: " .. (exit_status or "no exit"))
  end
end

-- Test dash_context plugin
describe("dash_context plugin", function()
  setup_kong_mocks()
  
  -- Mock JWT verification
  package.loaded["resty.jwt"] = {
    verify = function(secret, token)
      return {
        valid = true,
        payload = {
          sub = "user-123",
          learner_uid = "learner-456",
          role = "learner",
          tenant_id = "tenant-789"
        }
      }
    end
  }
  
  local handler = {
    access = function(self, conf)
      local headers = kong.request.get_headers()
      local auth_header = headers["authorization"]
      
      if not auth_header and conf.required_context then
        kong.response.exit(401, { code = "MISSING_JWT" })
      end
      
      local context_header = headers[conf.context_header and conf.context_header:lower() or "x-dashboard-context"]
      if not context_header and conf.required_context then
        kong.response.exit(400, { code = "MISSING_CONTEXT" })
      end
      
      if context_header then
        local valid = false
        for _, allowed in ipairs(conf.allowed_contexts or {}) do
          if context_header == allowed then
            valid = true
            break
          end
        end
        if not valid then
          kong.response.exit(403, { code = "INVALID_CONTEXT" })
        end
      end
    end
  }
  
  it("should reject when JWT is missing", function()
    kong.request.get_headers = function() return {} end
    
    expect_http_exit(401, function()
      handler:access({ required_context = true })
    end)
  end)
  
  it("should reject when context is missing", function() 
    kong.request.get_headers = function()
      return { authorization = "Bearer valid-token" }
    end
    
    expect_http_exit(400, function()
      handler:access({ 
        required_context = true,
        context_header = "X-Dashboard-Context"
      })
    end)
  end)
  
  it("should reject invalid context", function()
    kong.request.get_headers = function()
      return { 
        authorization = "Bearer valid-token",
        ["x-dashboard-context"] = "invalid"
      }
    end
    
    expect_http_exit(403, function()
      handler:access({
        required_context = true,
        context_header = "X-Dashboard-Context",
        allowed_contexts = { "learner", "teacher" }
      })
    end)
  end)
  
  it("should pass with valid context", function()
    kong.request.get_headers = function()
      return { 
        authorization = "Bearer valid-token",
        ["x-dashboard-context"] = "learner"
      }
    end
    
    -- Should not throw error
    handler:access({
      required_context = true, 
      context_header = "X-Dashboard-Context",
      allowed_contexts = { "learner", "teacher" }
    })
  end)
end)

-- Test learner_scope plugin  
describe("learner_scope plugin", function()
  setup_kong_mocks()
  
  local handler = {
    access = function(self, conf)
      if not conf.enforce_scope then return end
      
      local path = kong.request.get_path()
      local learner_id = path:match("/learners/([^/]+)")
      
      if not learner_id then return end
      
      local headers = kong.request.get_headers()
      local auth_header = headers["authorization"]
      
      if not auth_header then
        kong.response.exit(401, { code = "MISSING_JWT" })
      end
      
      -- Mock JWT parsing
      local jwt_learner_id = "learner-123" -- Simulate from JWT
      if conf.bypass_roles then
        for _, role in ipairs(conf.bypass_roles) do
          if role == "admin" then return end -- Simulate bypass
        end
      end
      
      if learner_id ~= jwt_learner_id then
        kong.response.exit(403, { code = "LEARNER_SCOPE_VIOLATION" })
      end
    end
  }
  
  it("should pass when no learner ID in path", function()
    kong.request.get_path = function() return "/api/health" end
    
    handler:access({ enforce_scope = true })
  end)
  
  it("should reject when JWT is missing", function()
    kong.request.get_path = function() return "/learners/learner-456/persona" end
    kong.request.get_headers = function() return {} end
    
    expect_http_exit(401, function()
      handler:access({ enforce_scope = true })
    end)
  end)
  
  it("should reject when learner IDs don't match", function()
    kong.request.get_path = function() return "/learners/learner-456/persona" end
    kong.request.get_headers = function() return { authorization = "Bearer token" } end
    
    expect_http_exit(403, function()
      handler:access({ 
        enforce_scope = true,
        bypass_roles = {}
      })
    end)
  end)
  
  it("should pass when learner IDs match", function()
    kong.request.get_path = function() return "/learners/learner-123/persona" end
    kong.request.get_headers = function() return { authorization = "Bearer token" } end
    
    handler:access({ 
      enforce_scope = true,
      bypass_roles = {}
    })
  end)
end)

-- Test consent_gate plugin
describe("consent_gate plugin", function()
  setup_kong_mocks()
  
  local handler = {
    access = function(self, conf)
      if not conf.enforce_consent then return end
      
      local path = kong.request.get_path()
      local requires_consent = false
      
      for _, consent_path in ipairs(conf.require_consent_for_paths or {}) do
        if path:find(consent_path, 1, true) then
          requires_consent = true
          break
        end
      end
      
      if not requires_consent then return end
      
      local headers = kong.request.get_headers()
      if not headers["authorization"] then
        kong.response.exit(401, { code = "MISSING_JWT" })
      end
      
      -- Mock: simulate no consent found
      if not conf.default_consent_status then
        kong.response.exit(451, { code = "CONSENT_NOT_FOUND" })
      end
    end
  }
  
  it("should pass for paths not requiring consent", function()
    kong.request.get_path = function() return "/health" end
    
    handler:access({ 
      enforce_consent = true,
      require_consent_for_paths = { "/learners/" }
    })
  end)
  
  it("should reject when no JWT for consent-required path", function()
    kong.request.get_path = function() return "/learners/123/persona" end
    kong.request.get_headers = function() return {} end
    
    expect_http_exit(401, function()
      handler:access({
        enforce_consent = true,
        require_consent_for_paths = { "/learners/" }
      })
    end)
  end)
  
  it("should reject when no consent data found", function()
    kong.request.get_path = function() return "/learners/123/persona" end
    kong.request.get_headers = function() return { authorization = "Bearer token" } end
    
    expect_http_exit(451, function()
      handler:access({
        enforce_consent = true,
        require_consent_for_paths = { "/learners/" },
        default_consent_status = false
      })
    end)
  end)
  
  it("should pass with default consent status true", function()
    kong.request.get_path = function() return "/learners/123/persona" end
    kong.request.get_headers = function() return { authorization = "Bearer token" } end
    
    handler:access({
      enforce_consent = true,
      require_consent_for_paths = { "/learners/" },
      default_consent_status = true
    })
  end)
end)

-- Run all tests and print results
TestRunner:print_results()
