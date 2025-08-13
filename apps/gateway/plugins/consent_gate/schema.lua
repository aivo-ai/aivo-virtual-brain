return {
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
