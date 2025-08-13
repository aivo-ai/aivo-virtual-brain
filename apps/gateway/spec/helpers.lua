-- Test helpers and utilities for Kong plugin tests
local helpers = {}

-- Mock Kong object for testing
function helpers.mock_kong()
  local kong_mock = {
    log = {
      debug = function(...) print("DEBUG:", ...) end,
      info = function(...) print("INFO:", ...) end,
      warn = function(...) print("WARN:", ...) end,
      err = function(...) print("ERROR:", ...) end,
    },
    request = {
      get_headers = function() return {} end,
      get_path = function() return "/" end,
    },
    service = {
      request = {
        set_header = function(name, value)
          print("SET_HEADER:", name, "=", value)
        end,
        get_header = function(name)
          return nil
        end,
      }
    },
    response = {
      exit = function(status, body)
        error("HTTP_EXIT: " .. status .. " - " .. (body and body.message or ""))
      end,
      set_header = function(name, value)
        print("RESPONSE_HEADER:", name, "=", value)
      end,
    },
    tools = {
      uuid = {
        uuid = function() return "test-uuid-123" end
      }
    }
  }
  
  return kong_mock
end

-- Create mock JWT token for testing
function helpers.create_mock_jwt(claims)
  local cjson = require "cjson"
  local base64 = require "base64"
  
  claims = claims or {}
  local header = { typ = "JWT", alg = "HS256" }
  
  local header_b64 = base64.encode(cjson.encode(header))
  local payload_b64 = base64.encode(cjson.encode(claims))
  local signature = "mock-signature"
  
  return header_b64 .. "." .. payload_b64 .. "." .. signature
end

-- Create mock Redis connection
function helpers.mock_redis()
  local redis_mock = {
    connect = function() return true, nil end,
    auth = function() return true, nil end,
    select = function() return true, nil end,
    get = function(key) return nil, nil end,
    setex = function(key, ttl, value) return true, nil end,
    close = function() end,
    set_timeout = function() end
  }
  
  return redis_mock
end

-- Assert HTTP exit was called with expected status
function helpers.assert_http_exit(expected_status, func, ...)
  local ok, err = pcall(func, ...)
  if ok then
    error("Expected HTTP exit but function completed normally")
  end
  
  local status = err:match("HTTP_EXIT: (%d+)")
  if not status then
    error("Expected HTTP exit but got: " .. err)
  end
  
  status = tonumber(status)
  if status ~= expected_status then
    error("Expected HTTP status " .. expected_status .. " but got " .. status)
  end
end

return helpers
