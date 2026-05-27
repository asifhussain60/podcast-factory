import SpendChart from './SpendChart';

interface BookFlight { slug: string; title: string; phase: string; phase_status: string; cost_to_date_usd: number; kind?: string; }
interface BookShipped { slug: string; title: string; shipped: string; episodes: number; cost_total_usd: number; }
interface Commit { sha: string; subject: string; date: string; }
interface Debt { id: string; title: string; severity: string; plain: string; }

interface Props {
  booksInFlight: BookFlight[];
  booksShipped: BookShipped[];
  recentCommits: Commit[];
  debt: Debt[];
  burn30d: number[];
  phaseTime: Record<string, number>;
  convergeAvg: number;
  shipFirstTry: number;
}

const PHASE_BADGE: Record<string, string> = {
  P0: 'is-blocked',
  P1: 'is-flight',
  P2: 'is-future',
};

export default function LiveExecution({
  booksInFlight,
  booksShipped,
  recentCommits,
  debt,
  burn30d,
  phaseTime,
  convergeAvg,
  shipFirstTry,
}: Props) {
  const total30 = burn30d.reduce((a, b) => a + b, 0);
  const totalCost = booksShipped.reduce((a, b) => a + b.cost_total_usd, 0);

  return (
    <div className="stack">

      {/* KPI stat strip */}
      <div className="stat-strip">
        <div className="stat-card s-blue">
          <div className="stat-card-icon"><i className="fa-solid fa-spinner" aria-hidden="true" /></div>
          <div className="stat-card-body">
            <div className="stat-card-value">{booksInFlight.length}</div>
            <div className="stat-card-label">In Flight</div>
          </div>
        </div>
        <div className="stat-card s-amber">
          <div className="stat-card-icon"><i className="fa-solid fa-coins" aria-hidden="true" /></div>
          <div className="stat-card-body">
            <div className="stat-card-value">${total30.toFixed(0)}</div>
            <div className="stat-card-label">Spend / 30d</div>
          </div>
        </div>
        <div className="stat-card s-green">
          <div className="stat-card-icon"><i className="fa-solid fa-book-open" aria-hidden="true" /></div>
          <div className="stat-card-body">
            <div className="stat-card-value">{booksShipped.length}</div>
            <div className="stat-card-label">Books Shipped</div>
          </div>
        </div>
        <div className="stat-card s-brown">
          <div className="stat-card-icon"><i className="fa-solid fa-arrow-trend-up" aria-hidden="true" /></div>
          <div className="stat-card-body">
            <div className="stat-card-value">{shipFirstTry}%</div>
            <div className="stat-card-label">First-try Ship</div>
          </div>
        </div>
      </div>

      {/* Books in flight */}
      <section className="stack">
        <h3>Books moving through the factory right now</h3>
        {booksInFlight.length === 0
          ? <p className="muted small">Nothing in flight at the moment.</p>
          : (
            <div className="grid-2">
              {booksInFlight.map((b) => (
                <div key={b.slug} className="card stack-tight">
                  {b.kind && <span className="eyebrow">{b.kind.replace(/-/g, ' ')}</span>}
                  <h3 className="card-title">{b.title}</h3>
                  <p className="small muted">At station: {b.phase}</p>
                  <div className="row-between">
                    <span className="step-badge is-flight">{b.phase_status}</span>
                    <span className="small muted">${b.cost_to_date_usd.toFixed(2)} so far</span>
                  </div>
                </div>
              ))}
            </div>
          )
        }
      </section>

      {/* Spend chart + converge metrics */}
      <section className="grid-2">
        <div className="stack spend-hero">
          <span className="eyebrow">Spend — last 30 days</span>
          <SpendChart values={burn30d} />
          <p className="small muted">
            ${total30.toFixed(2)} total · ${(total30 / 30).toFixed(2)}/day avg
          </p>
        </div>
        <div className="stack">
          <div className="card metric">
            <span className="metric-label">Quality passes per book on average</span>
            <span className="metric-value">{convergeAvg.toFixed(1)}</span>
            <span className="card-sub">How many reviewer cycles before a book converges.</span>
          </div>
          <div className="card metric">
            <span className="metric-label">Shipped on the first try</span>
            <span className="metric-value">{shipFirstTry}%</span>
            <span className="card-sub">Books that pass gates without a human override.</span>
          </div>
        </div>
      </section>

      {/* Known issues */}
      {debt.length > 0 && (
        <section className="stack">
          <h3>Known issues we're working around</h3>
          {debt.map((d) => (
            <div key={d.id} className="card card-tight">
              <div className="row-between">
                <strong>{d.title}</strong>
                <span className={`step-badge ${PHASE_BADGE[d.severity] ?? 'is-future'}`}>{d.severity}</span>
              </div>
              <p className="small muted">{d.plain}</p>
            </div>
          ))}
        </section>
      )}

      {/* Catalog */}
      <section className="stack">
        <h3>Already in the catalog</h3>
        <table className="data">
          <thead>
            <tr><th>Title</th><th>Shipped</th><th>Episodes</th><th>Cost</th></tr>
          </thead>
          <tbody>
            {booksShipped.map((b) => (
              <tr key={b.slug}>
                <td>{b.title}</td>
                <td>{b.shipped}</td>
                <td>{b.episodes}</td>
                <td>${b.cost_total_usd.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="small muted text-right">
          Total pipeline cost: ${totalCost.toFixed(2)}
        </p>
      </section>

      {/* Station times */}
      <section className="stack">
        <h3>How long each station takes on average</h3>
        <table className="data">
          <thead><tr><th>Station</th><th>Minutes</th></tr></thead>
          <tbody>
            {Object.entries(phaseTime).map(([name, min]) => (
              <tr key={name}><td>{name}</td><td>{min}</td></tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Recent commits */}
      <section className="stack">
        <h3>Recent changes</h3>
        <table className="data">
          <thead><tr><th>Date</th><th>What changed</th></tr></thead>
          <tbody>
            {recentCommits.map((c) => (
              <tr key={c.sha}><td>{c.date}</td><td>{c.subject}</td></tr>
            ))}
          </tbody>
        </table>
      </section>

    </div>
  );
}
