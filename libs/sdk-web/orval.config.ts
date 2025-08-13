import { defineConfig } from "orval";

export default defineConfig({
  auth: {
    input: "../../docs/api/rest/auth.yaml",
    output: {
      mode: "tags-split",
      target: "src/api/auth.ts",
      schemas: "src/types/auth.ts",
      client: "axios",
      mock: true,
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
  user: {
    input: "../../docs/api/rest/user.yaml",
    output: {
      mode: "tags-split",
      target: "src/api/user.ts",
      schemas: "src/types/user.ts",
      client: "axios",
      mock: true,
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
  assessment: {
    input: "../../docs/api/rest/assessment.yaml",
    output: {
      mode: "tags-split",
      target: "src/api/assessment.ts",
      schemas: "src/types/assessment.ts",
      client: "axios",
      mock: true,
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
  learner: {
    input: "../../docs/api/rest/learner.yaml",
    output: {
      mode: "tags-split",
      target: "src/api/learner.ts",
      schemas: "src/types/learner.ts",
      client: "axios",
      mock: true,
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
  notification: {
    input: "../../docs/api/rest/notification.yaml",
    output: {
      mode: "tags-split",
      target: "src/api/notification.ts",
      schemas: "src/types/notification.ts",
      client: "axios",
      mock: true,
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
  search: {
    input: "../../docs/api/rest/search.yaml",
    output: {
      mode: "tags-split",
      target: "src/api/search.ts",
      schemas: "src/types/search.ts",
      client: "axios",
      mock: true,
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
  orchestrator: {
    input: "../../docs/api/rest/orchestrator.yaml",
    output: {
      mode: "tags-split",
      target: "src/api/orchestrator.ts",
      schemas: "src/types/orchestrator.ts",
      client: "axios",
      mock: true,
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
});
