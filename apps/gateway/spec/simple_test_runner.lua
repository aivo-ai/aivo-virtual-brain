-- Simple Lua Test Runner for Kong Plugins
-- S1-09 Testing without Busted dependencies

-- Mock global objects
ngx = ngx or { null = "__null__" }

-- Load JSON library
local cjson = require("cjson") or {
  encode = function(t) return "{}" end,
  decode = function(s) return {} end
}

-- Load base64 library  
local base64 = {
  encode = function(s) return "base64_encoded" end,
  decode = function(s) return "base64_decoded" end
}

-- Test runner functions
local TestRunner = {
  tests = {},
  passed = 0,
  failed = 0,
  total = 0
}

function TestRunner:describe(name, func)
  print("\n=== " .. name .. " ===")
  func()
end

function TestRunner:it(name, func)
  self.total = self.total + 1
  io.write("  " .. name .. " ... ")
  
  local success, err = pcall(func)
  
  if success then
    print("PASS")
    self.passed = self.passed + 1
  else
    print("FAIL: " .. (err or "unknown error"))
    self.failed = self.failed + 1
  end
end

function TestRunner:assert_equal(expected, actual, message)
  if expected ~= actual then
    error(message or ("Expected " .. tostring(expected) .. " but got " .. tostring(actual)))
  end
end

function TestRunner:assert_true(condition, message)
  if not condition then
    error(message or "Expected condition to be true")
  end
end

function TestRunner:assert_error(func, message)
  local success, err = pcall(func)
  if success then
    error(message or "Expected function to throw an error")
  end
end

function TestRunner:print_results()
  print("\n" .. string.rep("=", 50))
  print("Test Results:")
  print("  Total: " .. self.total)
  print("  Passed: " .. self.passed)
  print("  Failed: " .. self.failed)
  print("  Success Rate: " .. math.floor((self.passed / self.total) * 100) .. "%")
  
  if self.failed == 0 then
    print("\n🎉 All tests passed!")
  else
    print("\n❌ Some tests failed.")
  end
end

-- Export globals for tests
describe = function(name, func) TestRunner:describe(name, func) end
it = function(name, func) TestRunner:it(name, func) end
assert = {
  equal = function(expected, actual, message) TestRunner:assert_equal(expected, actual, message) end,
  is_true = function(condition, message) TestRunner:assert_true(condition, message) end,
  has_error = function(func, message) TestRunner:assert_error(func, message) end
}

return TestRunner
