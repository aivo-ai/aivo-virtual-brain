-- AIVO Virtual Brains - Dash Context Plugin Tests
-- S1-09 Implementation Tests

local helpers = require "spec.helpers"

describe("dash_context plugin", function()
  local handler, kong_mock
  
  setup(function()
    -- Load the plugin handler
    handler = require("plugins.dash_context.handler").DashContextHandler
    
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
      header_prefix = "X-Dash-",
      context_header = "X-Dashboard-Context",
      user_id_header = "X-User-ID",
      tenant_id_header = "X-Tenant-ID",
      required_context = true,
      allowed_contexts = { "learner", "teacher", "guardian", "admin" }
    }

    describe("when JWT is missing", function()
      it("should return 401 if context is required", function()
        -- Mock request with no auth header
        kong_mock.request.get_headers = function()
          return {}
        end
        
        helpers.assert_http_exit(401, function()
          handler:access(default_config)
        end)
      end)
      
      it("should pass if context is not required", function()
        local config = {
          header_prefix = "X-Dash-",
          context_header = "X-Dashboard-Context", 
          user_id_header = "X-User-ID",
          tenant_id_header = "X-Tenant-ID",
          required_context = false,
          allowed_contexts = { "learner", "teacher", "guardian", "admin" }
        }
        
        kong_mock.request.get_headers = function()
          return {}
        end
        
        -- Should not raise an error
        handler:access(config)
      end)
    end)

    describe("when JWT is valid", function()
      it("should pass with valid context", function()
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-123",
          learner_uid = "learner-456", 
          role = "learner",
          tenant_id = "tenant-789"
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token,
            ["x-dashboard-context"] = "learner"
          }
        end
        
        local headers_set = {}
        kong_mock.service.request.set_header = function(name, value)
          headers_set[name] = value
        end
        
        handler:access(default_config)
        
        -- Verify headers were set
        assert.equal("user-123", headers_set["X-User-ID"])
        assert.equal("learner-456", headers_set["X-Dash-Learner-ID"])
        assert.equal("learner", headers_set["X-Dash-User-Role"])
        assert.equal("tenant-789", headers_set["X-Tenant-ID"])
        assert.equal("learner", headers_set["X-Dash-Context"])
      end)
      
      it("should reject invalid context", function()
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-123",
          role = "learner"
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token,
            ["x-dashboard-context"] = "invalid_context"
          }
        end
        
        helpers.assert_http_exit(403, function()
          handler:access(default_config)
        end)
      end)
      
      it("should require context header when required_context is true", function()
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-123",
          role = "learner"
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        helpers.assert_http_exit(400, function()
          handler:access(default_config)
        end)
      end)
    end)
  end)

  describe("header_filter phase", function()
    it("should add response headers", function()
      local config = default_config
      local response_headers = {}
      
      kong_mock.service.request.get_header = function(name)
        if name == "X-Dash-Context" then
          return "learner"
        end
        return nil
      end
      
      kong_mock.response.set_header = function(name, value)
        response_headers[name] = value
      end
      
      handler:header_filter(config)
      
      assert.equal("learner", response_headers["X-Dashboard-Context-Applied"])
      assert.equal("1.0.0", response_headers["X-Plugin-DashContext"])
    end)
  end)

  describe("configuration validation", function()
    it("should use default values", function()
      local config = {}
      
      -- Plugin should handle missing config gracefully
      local jwt_token = helpers.create_mock_jwt({
        sub = "user-123"
      })
      
      kong_mock.request.get_headers = function()
        return {
          authorization = "Bearer " .. jwt_token,
          ["x-dashboard-context"] = "learner"
        }
      end
      
      -- Should not error with empty config (defaults apply)
      handler:access(config)
    end)
  end)
end)
