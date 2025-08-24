// Stage-6 Service Handlers
import { 
  chatHandlers,
  scimHandlers, 
  verificationHandlers,
  taxHandlers,
  legalHoldHandlers,
  healthHandlers
} from './stage6';

import {
  residencyHandlers,
  sisBridgeHandlers,
  complianceHandlers,
  additionalHealthHandlers
} from './stage6-additional';

// Export all handlers
export {
  chatHandlers,
  scimHandlers,
  verificationHandlers,
  taxHandlers,
  legalHoldHandlers,
  healthHandlers,
  residencyHandlers,
  sisBridgeHandlers,
  complianceHandlers,
  additionalHealthHandlers
};

// Combined export for convenience
export const allStage6Handlers = [
  ...chatHandlers,
  ...scimHandlers,
  ...verificationHandlers,
  ...taxHandlers,
  ...legalHoldHandlers,
  ...healthHandlers,
  ...residencyHandlers,
  ...sisBridgeHandlers,
  ...complianceHandlers,
  ...additionalHealthHandlers,
];
