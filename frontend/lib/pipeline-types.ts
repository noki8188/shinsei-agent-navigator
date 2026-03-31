export type ClarificationItem = {
  field: string;
  reason: string;
  prompt: string;
  required: boolean;
};

export type PolicyDoc = {
  caseType: string;
  title: string;
  path: string;
  summary: string;
};

export type DraftResult = {
  title: string;
  body: string;
  attachments: string[];
  approvalRoute: string[];
  notes: string[];
};

export type ReviewResult = {
  missingFields: string[];
  policyRisks: string[];
  humanCheckpoints: string[];
};

export type PipelineTrace = {
  classification: {
    caseType: string;
    matchedKeywords: string[];
    rationale: string;
  };
  clarification: {
    extractedFields: string[];
    missingFields: string[];
    questions: string[];
  };
  ruleReferences: {
    documents: string[];
    appliedRules: string[];
  };
  review: {
    verdict: string;
    policyRisks: string[];
    humanCheckpoints: string[];
  };
  timeline: string[];
};

export type PipelineResponse = {
  caseType: string;
  policyDocs: PolicyDoc[];
  clarificationItems: ClarificationItem[];
  draftResult: DraftResult;
  reviewResult: ReviewResult;
  trace: PipelineTrace;
};
