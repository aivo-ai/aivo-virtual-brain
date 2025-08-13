return {
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
