import { ChatDemo } from "../components/chat-demo";

const agents = [
  {
    name: "Intake Agent",
    description: "自然言語の相談を読み、経費・備品購入・出張申請のどれに当たるか分類する。"
  },
  {
    name: "Policy Retrieval Agent",
    description: "Markdown 化された規程、FAQ、承認ルール、テンプレートから必要情報を集める。"
  },
  {
    name: "Clarification Agent",
    description: "金額、用途、見積書、出張先など不足情報を抽出し、確認質問へ変換する。"
  },
  {
    name: "Draft Generation Agent",
    description: "申請草稿、必要添付、承認ルート候補、注意点をまとめる。"
  },
  {
    name: "Review / Compliance Agent",
    description: "規程抵触の疑い、承認レベル、要人手確認事項を洗い出す。"
  },
  {
    name: "Logging / Ops Agent",
    description: "判断経路と保留事項を trace として残し、後続レビューと監査に備える。"
  }
];

export default function Home() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Agent-driven workflow support</p>
          <h1>社内申請ナビゲーター</h1>
          <p className="lead">
            日本企業でよくある申請・承認・問い合わせ業務を、複数 agent の分業で整理し、
            実務 PoC として見せるための最小実装です。
          </p>
        </div>
        <div className="hero-panel">
          <p>代替ではなく、分業の再設計</p>
          <ul>
            <li>agent は整理、補問、草稿、確認を担当</li>
            <li>人は最終判断、承認、例外対応を担当</li>
            <li>知識ソースは Markdown でレビュー可能に管理</li>
          </ul>
        </div>
      </section>

      <section className="insight-grid">
        <article className="insight-card">
          <h2>Before</h2>
          <ul>
            <li>ルールが分散して探しづらい</li>
            <li>確認先が分かりにくい</li>
            <li>ドラフト作成に時間がかかる</li>
            <li>問い合わせが集中しやすい</li>
          </ul>
        </article>

        <article className="insight-card">
          <h2>After</h2>
          <ul>
            <li>自然言語で相談できる</li>
            <li>不足情報を補問できる</li>
            <li>ドラフトと添付候補を生成できる</li>
            <li>承認ルート候補を提示できる</li>
          </ul>
        </article>
      </section>

      <section className="agent-section">
        <div className="panel-header">
          <p className="eyebrow">Multi-agent design</p>
          <h2>6 つの agent で業務を分割する</h2>
        </div>
        <div className="agent-grid">
          {agents.map((agent) => (
            <article key={agent.name} className="agent-card">
              <h3>{agent.name}</h3>
              <p>{agent.description}</p>
            </article>
          ))}
        </div>
      </section>

      <ChatDemo />
    </main>
  );
}

