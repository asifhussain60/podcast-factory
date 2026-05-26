import { useState } from 'react';
import Sparkline from './Sparkline';
import VendorLogo from './VendorLogo';

interface Service {
  id: string;
  name: string;
  plain: string;
  used_by: string[];
  month_cost_usd: number;
  alltime_cost_usd: number;
  calls_30d: number;
  daily_sparkline: number[];
}

interface Vendor {
  id: string;
  name: string;
  plain: string;
  services: Service[];
}

interface Props { vendors: Vendor[]; }

const VENDOR_KEYS: Record<string, 'anthropic' | 'google' | 'azure' | 'github'> = {
  anthropic: 'anthropic', google: 'google', azure: 'azure', github: 'github',
};

const LOGO_FOR_VENDOR: Record<string, 'anthropic' | 'google' | 'azure' | 'github' | 'notebooklm'> = {
  anthropic: 'anthropic', google: 'google', azure: 'azure', github: 'github',
};

export default function InfraColumns({ vendors }: Props) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  return (
    <div className="infra-grid">
      {vendors.map((v) => {
        const monthSum = v.services.reduce((s, x) => s + (x.month_cost_usd ?? 0), 0);
        return (
          <div key={v.id} className={`card stack vendor-col vendor-${v.id}`}>
            <header className="stack-tight">
              <div className="vendor-head-row">
                <VendorLogo vendor={LOGO_FOR_VENDOR[v.id] ?? 'anthropic'} size={40} />
                <div className="vendor-head-text">
                  <span className="eyebrow">Vendor</span>
                  <h3 className="card-title">{v.name}</h3>
                </div>
              </div>
              <p className="small muted">{v.plain}</p>
              <div className="row-between vendor-summary">
                <span className="metric-label">This month</span>
                <span className="vendor-total">${monthSum.toFixed(2)}</span>
              </div>
            </header>

            <div className="stack-tight">
              {v.services.map((svc) => {
                const key = `${v.id}/${svc.id}`;
                const open = openKey === key;
                return (
                  <div
                    key={svc.id}
                    className={`service-row hover-host ${open ? 'is-open' : ''}`}
                    onMouseEnter={() => setOpenKey(key)}
                    onMouseLeave={() => setOpenKey(null)}
                    onFocus={() => setOpenKey(key)}
                    onBlur={() => setOpenKey(null)}
                    tabIndex={0}
                    role="button"
                    aria-label={`${svc.name} — see cost detail`}
                  >
                    <div className="row-between service-line">
                      <span className="service-name">{svc.name}</span>
                      <span className="service-cost">${svc.month_cost_usd.toFixed(2)}</span>
                    </div>
                    <div className="hover-tip">
                      <h4>{svc.name}</h4>
                      <p className="small">{svc.plain}</p>
                      <div className="kv"><span className="k">This month</span><span className="v">${svc.month_cost_usd.toFixed(2)}</span></div>
                      <div className="kv"><span className="k">All time</span><span className="v">${svc.alltime_cost_usd.toFixed(2)}</span></div>
                      <div className="kv"><span className="k">Calls (30d)</span><span className="v">{svc.calls_30d.toLocaleString()}</span></div>
                      {svc.used_by.length > 0 && (
                        <div className="kv tip-stations"><span className="k">Used at</span><span className="v">{svc.used_by.length} station{svc.used_by.length === 1 ? '' : 's'}</span></div>
                      )}
                      <Sparkline values={svc.daily_sparkline} vendor={VENDOR_KEYS[v.id] ?? 'anthropic'} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
