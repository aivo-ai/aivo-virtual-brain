-- AIVO Virtual Brains - Learner Scope Plugin Tests
-- S1-09 Implementation Tests

local helpers = require "spec.helpers"

describe("learner_scope plugin", function()
  local handler, kong_mock
  
  setup(function()
    -- Load the plugin handler
    handler = require("plugins.learner_scope.handler").LearnerScopeHandler
    
    -- Mock Kong
    kong_mock = helpers.mock_kong()
    _G.kong = kong_mock
  end)
  
  before_each(function()
    -- Reset mocks
    kong_mock = helpers.mock_kong()
    _G.kong = kong_mock
  end)

  describe("access phase", function()
    local default_config = {
      learner_param_name = "learnerId",
      jwt_learner_claim = "learner_uid",
      bypass_roles = { "admin", "teacher" },
      enforce_scope = true,
      error_response = {
        status = 403,
        message = "Learner scope violation: Access denied",
        code = "LEARNER_SCOPE_VIOLATION"
      }
    }

    describe("path without learner ID", function()
      it("should pass when no learner ID in path", function()
        kong_mock.request.get_path = function()
          return "/api/health"
        end
        
        -- Should not raise an error
        handler:access(default_config)
      end)
    end)

    describe("path with learner ID", function()
      it("should enforce scope matching when learner ID in path", function()
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-456",
          learner_uid = "learner-123",
          role = "learner"
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        local headers_set = {}
        kong_mock.service.request.set_header = function(name, value)
          headers_set[name] = value
        end
        
        handler:access(default_config)
        
        -- Verify validation headers were set
        assert.equal("learner-123", headers_set["X-Validated-Learner-ID"])
        assert.equal("true", headers_set["X-Learner-Scope-Validated"])
      end)
      
      it("should reject when learner ID mismatch", function()
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-456",
          learner_uid = "learner-999", -- Different from path
          role = "learner"
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        helpers.assert_http_exit(403, function()
          handler:access(default_config)
        end)
      end)
      
      it("should reject when no JWT provided", function()
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        kong_mock.request.get_headers = function()
          return {}
        end
        
        helpers.assert_http_exit(401, function()
          handler:access(default_config)
        end)
      end)
      
      it("should reject when no learner_uid in JWT", function()
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-456",
          role = "learner"
          -- No learner_uid claim
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        helpers.assert_http_exit(403, function()
          handler:access(default_config)
        end)
      end)
    end)

    describe("bypass roles", function()
      it("should allow admin role to bypass scope check", function()
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "admin-456",
          learner_uid = "learner-999", -- Different from path
          role = "admin" -- Admin can bypass
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        -- Should not raise an error
        handler:access(default_config)
      end)
      
      it("should allow teacher role to bypass scope check", function()
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "teacher-456",
          learner_uid = "learner-999", -- Different from path
          role = "teacher" -- Teacher can bypass
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        -- Should not raise an error
        handler:access(default_config)
      end)
      
      it("should not allow learner role to bypass scope check", function()
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-456",
          learner_uid = "learner-999", -- Different from path
          role = "learner" -- Learner cannot bypass
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        helpers.assert_http_exit(403, function()
          handler:access(default_config)
        end)
      end)
    end)

    describe("path extraction", function()
      it("should extract learner ID from various path patterns", function()
        local test_paths = {
          "/learners/learner-123",
          "/api/learners/learner-456/persona", 
          "/learners/learner-789/model-bindings",
          "/api/v1/learners/learner-abc/private-brain"
        }
        
        local expected_ids = {
          "learner-123",
          "learner-456",
          "learner-789", 
          "learner-abc"
        }
        
        for i, path in ipairs(test_paths) do
          kong_mock.request.get_path = function()
            return path
          end
          
          local jwt_token = helpers.create_mock_jwt({
            sub = "user-456",
            learner_uid = expected_ids[i],
            role = "learner"
          })
          
          kong_mock.request.get_headers = function()
            return {
              authorization = "Bearer " .. jwt_token
            }
          end
          
          -- Should not raise an error (IDs match)
          handler:access(default_config)
        end
      end)
    end)

    describe("enforcement disabled", function()
      it("should skip validation when enforce_scope is false", function()
        local config = {
          learner_param_name = "learnerId",
          jwt_learner_claim = "learner_uid",
          bypass_roles = { "admin", "teacher" },
          enforce_scope = false, -- Disabled
          error_response = {
            status = 403,
            message = "Learner scope violation: Access denied",
            code = "LEARNER_SCOPE_VIOLATION"
          }
        }
        
        kong_mock.request.get_path = function()
          return "/api/learners/learner-123/persona"
        end
        
        -- Should not raise an error even without JWT
        handler:access(config)
      end)
    end)
  end)

  describe("header_filter phase", function()
    it("should add response headers", function()
      local config = default_config
      local response_headers = {}
      
      kong_mock.service.request.get_header = function(name)
        if name == "X-Learner-Scope-Validated" then
          return "true"
        end
        return nil
      end
      
      kong_mock.response.set_header = function(name, value)
        response_headers[name] = value
      end
      
      handler:header_filter(config)
      
      assert.equal("1.0.0", response_headers["X-Plugin-LearnerScope"])
      assert.equal("validated", response_headers["X-Learner-Scope-Status"])
    end)
  end)
end)
