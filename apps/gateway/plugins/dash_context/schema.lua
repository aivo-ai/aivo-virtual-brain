return {
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
