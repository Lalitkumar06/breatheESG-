import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, TrendingUp, Clock, Leaf } from 'lucide-react';
import { dashboardAPI } from '../api/client';
import StatusBadge from '../components/StatusBadge';

// ─── Minimal SVG Pie Chart ────────────────────────────────────────────────────
function PieChart({ data }: { data: { name: string; value: number; color: string }[] }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return <div style={{ textAlign: 'center', color: 'var(--text-muted)', paddingTop: 60 }}>No data</div>;

  let cumAngle = -Math.PI / 2;
  const cx = 80, cy = 80, r = 60, ir = 36;

  const slices = data.map(d => {
    const angle = (d.value / total) * 2 * Math.PI;
    const start = cumAngle;
    cumAngle += angle;
    const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start);
    const x2 = cx + r * Math.cos(cumAngle), y2 = cy + r * Math.sin(cumAngle);
    const ix1 = cx + ir * Math.cos(start), iy1 = cy + ir * Math.sin(start);
    const ix2 = cx + ir * Math.cos(cumAngle), iy2 = cy + ir * Math.sin(cumAngle);
    const large = angle > Math.PI ? 1 : 0;
    return {
      ...d,
      path: `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${ir} ${ir} 0 ${large} 0 ${ix1} ${iy1} Z`,
      pct: ((d.value / total) * 100).toFixed(1),
    };
  });

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <svg width={160} height={160} viewBox="0 0 160 160">
        {slices.map((s, i) => (
          <path key={i} d={s.path} fill={s.color} opacity={0.9} />
        ))}
      </svg>
      <div style={{ flex: 1 }}>
        {slices.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: s.color, flexShrink: 0 }} />
            <div style={{ flex: 1, fontSize: 12, color: 'var(--text-secondary)' }}>{s.name}</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }} className="mono">
              {s.pct}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Minimal SVG Bar Chart ────────────────────────────────────────────────────
function BarChart({ data }: { data: { name: string; value: number; color: string }[] }) {
  const max = Math.max(...data.map(d => d.value), 1);
  const w = 280, h = 140, barW = 50, gap = 20;

  return (
    <svg width={w} height={h + 24} viewBox={`0 0 ${w} ${h + 24}`}>
      {data.map((d, i) => {
        const bh = Math.max((d.value / max) * h, 2);
        const x = i * (barW + gap) + 10;
        const y = h - bh;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={bh} rx={4} fill={d.color} opacity={0.85} />
            <text x={x + barW / 2} y={h + 16} textAnchor="middle" fontSize={11} fill="var(--text-muted)">{d.name}</text>
            {d.value > 0 && (
              <text x={x + barW / 2} y={y - 4} textAnchor="middle" fontSize={10} fill={d.color} fontWeight={700}>
                {d.value >= 1000 ? `${(d.value / 1000).toFixed(1)}t` : d.value.toFixed(0)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
const SCOPE_COLORS = ['#ff6b6b', '#4dabf7', '#69db7c'];
const SOURCE_COLORS: Record<string, string> = { SAP: '#82b1ff', UTILITY: '#69db7c', TRAVEL: '#ffd180' };

function ScopeCard({ label, total_co2e_kg, record_count, color, accent }: any) {
  return (
    <div className="glass-card metric-card" style={{ position: 'relative', padding: 20, overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 3,
        background: color, borderRadius: '12px 12px 0 0',
      }} />
      <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: accent || 'var(--text-primary)', marginBottom: 4 }} className="mono">
        {(total_co2e_kg || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
        kg CO₂e · {record_count || 0} records
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    dashboardAPI.summary()
      .then(res => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div className="loader" style={{ width: 40, height: 40 }} />
      </div>
    );
  }

  if (!data) return <div className="alert alert-error" style={{ margin: 24 }}>Failed to load dashboard data.</div>;

  const s1 = data.scope_totals?.scope_1 || { total_co2e_kg: 0, record_count: 0 };
  const s2 = data.scope_totals?.scope_2 || { total_co2e_kg: 0, record_count: 0 };
  const s3 = data.scope_totals?.scope_3 || { total_co2e_kg: 0, record_count: 0 };

  const pieData = [
    { name: 'Scope 1', value: s1.total_co2e_kg, color: SCOPE_COLORS[0] },
    { name: 'Scope 2', value: s2.total_co2e_kg, color: SCOPE_COLORS[1] },
    { name: 'Scope 3', value: s3.total_co2e_kg, color: SCOPE_COLORS[2] },
  ];

  const barData = (data.source_breakdown || []).map((s: any) => ({
    name: s.source,
    value: s.total_co2e_kg,
    color: SOURCE_COLORS[s.source] || '#8ba3c7',
  }));

  return (
    <div style={{ padding: '24px', maxWidth: 1400 }} className="animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Leaf size={20} style={{ color: 'var(--accent-green)' }} /> ESG Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            Tenant: <span style={{ color: 'var(--text-secondary)' }}>{data.tenant}</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {data.flagged_count > 0 && (
            <div className="alert alert-warning" style={{ padding: '7px 12px', cursor: 'pointer', fontSize: 12 }}
              onClick={() => navigate('/review?status=FLAGGED')}>
              <AlertTriangle size={13} /> {data.flagged_count} flagged
            </div>
          )}
          {data.pending_review_count > 0 && (
            <div className="alert alert-info" style={{ padding: '7px 12px', cursor: 'pointer', fontSize: 12 }}
              onClick={() => navigate('/review')}>
              <Clock size={13} /> {data.pending_review_count} pending review
            </div>
          )}
        </div>
      </div>

      {/* Total CO2e hero card */}
      <div className="glass-card" style={{
        padding: '20px 24px', marginBottom: 16,
        background: 'linear-gradient(135deg, rgba(0,230,118,0.06) 0%, rgba(41,121,255,0.06) 100%)',
        borderColor: 'rgba(0,230,118,0.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 6 }}>Total CO₂e — All Scopes</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ fontSize: 40, fontWeight: 800, color: 'var(--text-primary)' }} className="mono">
              {((data.total_co2e_kg || 0) / 1000).toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </span>
            <span style={{ fontSize: 18, color: 'var(--text-muted)' }}>tCO₂e</span>
          </div>
        </div>
        <TrendingUp size={36} style={{ color: 'var(--accent-green)', opacity: 0.5 }} />
      </div>

      {/* Scope Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
        <ScopeCard label="Scope 1 · Direct Emissions" {...s1} color={SCOPE_COLORS[0]} accent="#ff6b6b" />
        <ScopeCard label="Scope 2 · Electricity" {...s2} color={SCOPE_COLORS[1]} accent="#4dabf7" />
        <ScopeCard label="Scope 3 · Value Chain" {...s3} color={SCOPE_COLORS[2]} accent="#69db7c" />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 14 }}>CO₂e by Scope</h3>
          <PieChart data={pieData} />
        </div>
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 14 }}>CO₂e by Source</h3>
          <BarChart data={barData} />
        </div>
      </div>

      {/* Status + Recent Jobs */}
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 16 }}>
        {/* Status counts */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 12 }}>Records by Status</h3>
          {Object.entries(data.status_counts || {}).map(([key, count]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <StatusBadge status={key.toUpperCase()} size="sm" />
              <span className="mono" style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 700 }}>{String(count)}</span>
            </div>
          ))}
        </div>

        {/* Recent Jobs */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 12 }}>Recent Ingestion Jobs</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Rows</th>
                  <th>Errors</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {(data.recent_jobs || []).map((job: any) => (
                  <tr key={job.id} style={{ cursor: 'pointer' }} onClick={() => navigate('/jobs')}>
                    <td style={{ color: 'var(--text-primary)', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {job.filename}
                    </td>
                    <td><span className={`badge badge-${job.source_type?.toLowerCase()}`}>{job.source_type}</span></td>
                    <td><StatusBadge status={job.status} size="sm" /></td>
                    <td className="mono">{job.row_count}</td>
                    <td className="mono" style={{ color: job.error_count > 0 ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                      {job.error_count}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(job.uploaded_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
                {!data.recent_jobs?.length && (
                  <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20 }}>No jobs yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
