"use client";

import { FormEvent, useState } from "react";

type ClarificationItem = {
  field: string;
  reason: string;
  prompt: string;
  required: boolean;
};

type PolicyDoc = {
  caseType: string;
  title: string;
  path: string;
  summary: string;
};

type DraftResult = {
  title: string;
  body: string;
  attachments: string[];
  approvalRoute: string[];
  notes: string[];
};

type ReviewResult = {
  missingFields: string[];
  policyRisks: string[];
  humanCheckpoints: string[];
};

type PipelineTrace = {
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

type PipelineResponse = {
  caseType: string;
  policyDocs: PolicyDoc[];
  clarificationItems: ClarificationItem[];
  draftResult: DraftResult;
  reviewResult: ReviewResult;
  trace: PipelineTrace;
};

const samplePrompts = [
  "在宅勤務用に 27 インチモニターを 1 台買いたいです。予算は 8 万円くらいです",
  "先週の会食代を精算したいです。金額は 12,000 円です",
  "大阪へ 2 日間の出張申請を出したいです。目的は顧客訪問です"
];

export function ChatDemo() {
  const [message, setMessage] = useState(samplePrompts[0]);
  const [result, setResult] = useState<PipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const apiBaseUrl =
        process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

      const response = await fetch(`${apiBaseUrl}/api/chat/demo`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
      });

      if (!response.ok) {
        throw new Error("バックエンドから有効な応答を取得できませんでした。");
      }

      const payload = (await response.json()) as PipelineResponse;
      setResult(payload);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "不明なエラーが発生しました。"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="demo-panel">
      <div className="panel-header">
        <p className="eyebrow">Interactive PoC</p>
        <h2>相談入力から申請ドラフトまで確認する</h2>
        <p className="supporting-copy">
          Python バックエンドが起動していれば、分類、補問、草稿、レビュー結果を返します。
        </p>
      </div>

      <div className="sample-prompt-list">
        {samplePrompts.map((prompt) => (
          <button
            key={prompt}
            className="ghost-button"
            type="button"
            onClick={() => setMessage(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <label htmlFor="message">相談内容</label>
        <textarea
          id="message"
          name="message"
          rows={5}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="例: モニターを購入したいので、申請の流れと必要な添付を教えてください"
        />
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "解析中..." : "agent に相談する"}
        </button>
      </form>

      {error ? <p className="error-banner">{error}</p> : null}

      {result ? (
        <div className="result-grid">
          <article className="result-card">
            <h3>分類結果</h3>
            <p className="result-type">{result.caseType}</p>
            <p className="supporting-copy">{result.trace.classification.rationale}</p>
            <ul>
              {result.policyDocs.map((doc) => (
                <li key={doc.path}>
                  <strong>{doc.title}</strong>
                  <span>{doc.summary}</span>
                </li>
              ))}
            </ul>
          </article>

          <article className="result-card">
            <h3>補問候補</h3>
            <ul>
              {result.clarificationItems.length > 0 ? (
                result.clarificationItems.map((item) => (
                  <li key={item.field}>{item.prompt}</li>
                ))
              ) : (
                <li>不足情報は検出されませんでした。</li>
              )}
            </ul>
          </article>

          <article className="result-card result-card-wide">
            <h3>申請草稿</h3>
            <p className="draft-title">{result.draftResult.title}</p>
            <pre>{result.draftResult.body}</pre>
            <div className="tag-row">
              {result.draftResult.attachments.map((item) => (
                <span key={item} className="tag">
                  {item}
                </span>
              ))}
            </div>
          </article>

          <article className="result-card">
            <h3>承認ルート候補</h3>
            <ol>
              {result.draftResult.approvalRoute.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </article>

          <article className="result-card">
            <h3>レビュー結果</h3>
            <ul>
              {result.reviewResult.missingFields.map((field) => (
                <li key={field}>不足項目: {field}</li>
              ))}
              {result.reviewResult.policyRisks.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
              {result.reviewResult.humanCheckpoints.map((checkpoint) => (
                <li key={checkpoint}>{checkpoint}</li>
              ))}
            </ul>
          </article>

          <article className="result-card">
            <h3>申請メモ</h3>
            <ul>
              {result.draftResult.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </article>

          <article className="result-card result-card-wide">
            <h3>agent trace</h3>
            <div className="trace-grid">
              <section className="trace-block">
                <div className="trace-header">
                  <h4>分類</h4>
                  <span className="trace-pill">{result.trace.classification.caseType}</span>
                </div>
                <p>{result.trace.classification.rationale}</p>
                <div className="tag-row">
                  {result.trace.classification.matchedKeywords.length > 0 ? (
                    result.trace.classification.matchedKeywords.map((keyword) => (
                      <span key={keyword} className="tag">
                        {keyword}
                      </span>
                    ))
                  ) : (
                    <span className="trace-empty">一致キーワードなし</span>
                  )}
                </div>
              </section>

              <section className="trace-block">
                <div className="trace-header">
                  <h4>補問</h4>
                  <span className="trace-pill">
                    {result.trace.clarification.missingFields.length} 件
                  </span>
                </div>
                <p>抽出済み: {result.trace.clarification.extractedFields.join(", ") || "なし"}</p>
                <ul>
                  {result.trace.clarification.questions.length > 0 ? (
                    result.trace.clarification.questions.map((question) => (
                      <li key={question}>{question}</li>
                    ))
                  ) : (
                    <li>追加確認は不要でした。</li>
                  )}
                </ul>
              </section>

              <section className="trace-block">
                <div className="trace-header">
                  <h4>参照ルール</h4>
                  <span className="trace-pill">
                    {result.trace.ruleReferences.documents.length} docs
                  </span>
                </div>
                <ul>
                  {result.trace.ruleReferences.appliedRules.map((rule) => (
                    <li key={rule}>{rule}</li>
                  ))}
                </ul>
              </section>

              <section className="trace-block">
                <div className="trace-header">
                  <h4>レビュー</h4>
                  <span className="trace-pill trace-pill-accent">
                    {result.trace.review.verdict}
                  </span>
                </div>
                <ul>
                  {result.trace.review.policyRisks.length > 0 ? (
                    result.trace.review.policyRisks.map((risk) => (
                      <li key={risk}>{risk}</li>
                    ))
                  ) : (
                    <li>顕著な規程リスクは検出されませんでした。</li>
                  )}
                </ul>
                <p className="trace-subtitle">人が確認するポイント</p>
                <ul>
                  {result.trace.review.humanCheckpoints.map((checkpoint) => (
                    <li key={checkpoint}>{checkpoint}</li>
                  ))}
                </ul>
              </section>
            </div>

            <div className="trace-timeline">
              <p className="trace-subtitle">Timeline</p>
              <ol>
                {result.trace.timeline.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>
          </article>
        </div>
      ) : null}
    </section>
  );
}
