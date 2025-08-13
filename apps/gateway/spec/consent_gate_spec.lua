-- AIVO Virtual Brains - Consent Gate Plugin Tests
-- S1-09 Implementation Tests

local helpers = require "spec.helpers"

describe("consent_gate plugin", function()
  local handler, kong_mock, redis_mock
  
  setup(function()
    -- Load the plugin handler
    handler = require("plugins.consent_gate.handler").ConsentGateHandler
    
    -- Mock Kong
    kong_mock = helpers.mock_kong()
    _G.kong = kong_mock
    
    -- Mock Redis
    redis_mock = helpers.mock_redis()
  end)
  
  before_each(function()
    -- Reset mocks
    kong_mock = helpers.mock_kong()
    _G.kong = kong_mock
    redis_mock = helpers.mock_redis()
  end)

  describe("access phase", function()
    local default_config = {
      redis_host = "redis",
      redis_port = 6379,
      redis_timeout = 1000,
      redis_database = 0,
      consent_key_prefix = "consent:",
      cache_ttl = 3600,
      require_consent_for_paths = { "/learners/", "/persona/", "/private-brain/" },
      bypass_roles = { "admin" },
      enforce_consent = true,
      default_consent_status = false
    }

    describe("paths that don't require consent", function()
      it("should pass for health check endpoints", function()
        kong_mock.request.get_path = function()
          return "/health"
        end
        
        -- Should not raise an error
        handler:access(default_config)
      end)
      
      it("should pass for public API endpoints", function()
        kong_mock.request.get_path = function()
          return "/api/public/status"
        end
        
        -- Should not raise an error
        handler:access(default_config)
      end)
    end)

    describe("paths that require consent", function()
      it("should reject when no JWT provided", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
        end
        
        kong_mock.request.get_headers = function()
          return {}
        end
        
        helpers.assert_http_exit(401, function()
          handler:access(default_config)
        end)
      end)
      
      it("should reject when no learner ID in JWT", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-456",
          role = "learner"
          -- No learner_uid
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
      
      it("should pass when consent is granted", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
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
        
        -- Mock Redis to return consent granted
        local cjson = require "cjson"
        redis_mock.get = function(key)
          if key == "consent:learner-123" then
            return cjson.encode({
              status = true,
              timestamp = os.time(),
              cached = true
            })
          end
          return nil, nil
        end
        
        -- Mock Redis connection
        package.loaded["resty.redis"] = {
          new = function()
            return redis_mock
          end
        }
        
        local headers_set = {}
        kong_mock.service.request.set_header = function(name, value)
          headers_set[name] = value
        end
        
        handler:access(default_config)
        
        -- Verify consent headers were set
        assert.equal("true", headers_set["X-Consent-Validated"])
        assert.equal("learner-123", headers_set["X-Consent-Learner-ID"])
      end)
      
      it("should reject when consent is denied", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
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
        
        -- Mock Redis to return consent denied
        local cjson = require "cjson"
        redis_mock.get = function(key)
          if key == "consent:learner-123" then
            return cjson.encode({
              status = false, -- Consent denied
              timestamp = os.time(),
              cached = true
            })
          end
          return nil, nil
        end
        
        -- Mock Redis connection
        package.loaded["resty.redis"] = {
          new = function()
            return redis_mock
          end
        }
        
        helpers.assert_http_exit(451, function()
          handler:access(default_config)
        end)
      end)
      
      it("should reject when no consent data found", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
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
        
        -- Mock Redis to return no data
        redis_mock.get = function(key)
          return ngx.null, nil
        end
        
        -- Mock Redis connection
        package.loaded["resty.redis"] = {
          new = function()
            return redis_mock
          end
        }
        
        helpers.assert_http_exit(451, function()
          handler:access(default_config)
        end)
      end)
    end)

    describe("bypass roles", function()
      it("should allow admin role to bypass consent check", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "admin-456",
          learner_uid = "learner-123",
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
      
      it("should not allow learner role to bypass consent check", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
        end
        
        local jwt_token = helpers.create_mock_jwt({
          sub = "user-456",
          learner_uid = "learner-123",
          role = "learner" -- Learner cannot bypass
        })
        
        kong_mock.request.get_headers = function()
          return {
            authorization = "Bearer " .. jwt_token
          }
        end
        
        -- Mock Redis to return no data (should fail)
        redis_mock.get = function(key)
          return ngx.null, nil
        end
        
        package.loaded["resty.redis"] = {
          new = function()
            return redis_mock
          end
        }
        
        helpers.assert_http_exit(451, function()
          handler:access(default_config)
        end)
      end)
    end)

    describe("Redis connection errors", function()
      it("should handle Redis connection failure gracefully", function()
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
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
        
        -- Mock Redis connection failure
        package.loaded["resty.redis"] = {
          new = function()
            local red = {
              set_timeout = function() end,
              connect = function() return false, "connection failed" end,
              close = function() end
            }
            return red
          end
        }
        
        -- Should return 503 with default consent status false
        helpers.assert_http_exit(503, function()
          handler:access(default_config)
        end)
      end)
      
      it("should use default consent status when Redis fails", function()
        local config_with_default_true = {
          redis_host = "redis",
          redis_port = 6379,
          redis_timeout = 1000,
          redis_database = 0,
          consent_key_prefix = "consent:",
          cache_ttl = 3600,
          require_consent_for_paths = { "/learners/", "/persona/", "/private-brain/" },
          bypass_roles = { "admin" },
          enforce_consent = true,
          default_consent_status = true -- Default to true
        }
        
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
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
        
        -- Mock Redis connection failure
        package.loaded["resty.redis"] = {
          new = function()
            local red = {
              set_timeout = function() end,
              connect = function() return false, "connection failed" end,
              close = function() end
            }
            return red
          end
        }
        
        local headers_set = {}
        kong_mock.service.request.set_header = function(name, value)
          headers_set[name] = value
        end
        
        -- Should pass with default consent status true
        handler:access(config_with_default_true)
        
        assert.equal("true", headers_set["X-Consent-Validated"])
      end)
    end)

    describe("enforcement disabled", function()
      it("should skip validation when enforce_consent is false", function()
        local config = {
          redis_host = "redis",
          redis_port = 6379,
          redis_timeout = 1000,
          redis_database = 0,
          consent_key_prefix = "consent:",
          cache_ttl = 3600,
          require_consent_for_paths = { "/learners/", "/persona/", "/private-brain/" },
          bypass_roles = { "admin" },
          enforce_consent = false, -- Disabled
          default_consent_status = false
        }
        
        kong_mock.request.get_path = function()
          return "/learners/123/persona"
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
        if name == "X-Consent-Validated" then
          return "true"
        end
        return nil
      end
      
      kong_mock.response.set_header = function(name, value)
        response_headers[name] = value
      end
      
      handler:header_filter(config)
      
      assert.equal("1.0.0", response_headers["X-Plugin-ConsentGate"])
      assert.equal("validated", response_headers["X-Consent-Status"])
    end)
  end)
end)
