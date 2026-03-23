# インターフェース定義

## UserRequest

自然言語の相談入力。

```ts
type UserRequest = {
  message: string;
  applicant?: string;
  department?: string;
};
```

## CaseType

```ts
type CaseType = "expense" | "purchase" | "business_trip";
```

## PolicyDoc

Markdown ベースの規程、FAQ、承認ルール、申請テンプレート。

```ts
type PolicyDoc = {
  caseType: CaseType;
  title: string;
  path: string;
  summary: string;
};
```

## ClarificationItem

追加で確認すべき項目。

```ts
type ClarificationItem = {
  field: string;
  reason: string;
  prompt: string;
  required: boolean;
};
```

## DraftResult

申請草稿、必要添付、承認経路候補、注意点。

```ts
type DraftResult = {
  title: string;
  body: string;
  attachments: string[];
  approvalRoute: string[];
  notes: string[];
};
```

## ReviewResult

不足情報、規程抵触の疑い、要人手確認事項。

```ts
type ReviewResult = {
  missingFields: string[];
  policyRisks: string[];
  humanCheckpoints: string[];
};
```

## PipelineResponse

```ts
type PipelineTrace = {
  classification: {
    caseType: CaseType;
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
    verdict: "ready_with_review" | "needs_follow_up";
    policyRisks: string[];
    humanCheckpoints: string[];
  };
  timeline: string[];
};

type PipelineResponse = {
  caseType: CaseType;
  policyDocs: PolicyDoc[];
  clarificationItems: ClarificationItem[];
  draftResult: DraftResult;
  reviewResult: ReviewResult;
  trace: PipelineTrace;
};
```
