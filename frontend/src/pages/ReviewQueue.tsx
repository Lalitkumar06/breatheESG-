import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Check, X, Flag, RefreshCw } from 'lucide-react';
import { recordsAPI } from '../api/client';
import StatusBadge from '../components/StatusBadge';

const SCOPES = ['', '1', '2', '3'];
const SOURCES = ['', 'SAP', 'UTILITY', 'TRAVEL'];
const STATUSES = ['', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'FLAGGED'];
const CATEGORIES = ['', 'FUEL', 'ELECTRICITY', 'FLIGHT', 'HOTEL', 'GROUND', 'PROCUREMENT'];

function formatCO2(v: number | null) {
  if (v == null) return '—';
  return v >= 1000
    ? `${(v / 1000).toFixed(2)} tCO₂e`
    : `${v.toFixed(2)} kg`;
}

export default function ReviewQueue() {
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState({ scope: '', source_type: '', status: '', category: '', date_from: '', date_to: '' });
  const [actionModal, setActionModal] = useState<{ id: string; type: 'reject' | 'flag' } | null>(null);
  const [actionReason, setActionReason] = useState('');
  const [acting, setActing] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const loadRecords = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
    // Pick up status from URL
    const urlStatus = searchParams.get('status');
    if (urlStatus && !filters.status) params.status = urlStatus;

    recordsAPI.list(params)
      .then(res => setRecords(res.data.results || res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [filters, searchParams]);

  useEffect(() => { loadRecords(); }, [loadRecords]);

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const selectAll = () => {
    if (selected.size === records.length) setSelected(new Set());
    else setSelected(new Set(records.map(r => r.id)));
  };

  const doApprove = async (id: string) => {
    setActing(id);
    await recordsAPI.approve(id).catch(console.error);
    setActing(null);
    loadRecords();
  };

  const doAction = async () => {
    if (!actionModal) return;
    setActing(actionModal.id);
    if (actionModal.type === 'reject') await recordsAPI.reject(actionModal.id, actionReason).catch(console.error);
    if (actionModal.type === 'flag') await recordsAPI.flag(actionModal.id, actionReason).catch(console.error);
    setActionModal(null);
    setActionReason('');
    setActing(null);
    loadRecords();
  };

  const doBulkApprove = async () => {
    await recordsAPI.bulkApprove(Array.from(selected)).catch(console.error);
    setSelected(new Set());
    loadRecords();
  };

  const FilterSelect = ({ name, options }: { name: string; options: string[] }) => (
    <select value={filters[name as keyof typeof filters]}
      onChange={e => setFilters(f => ({ ...f, [name]: e.target.value }))}
      style={{ width: 130 }}>
      {options.map(o => <option key={o} value={o}>{o || `All ${name.replace('_', ' ')}`}</option>)}
    </select>
  );

  return (
    <div style={{ padding: 24 }} className="animate-fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Review Queue</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 2 }}>{records.length} records</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {selected.size > 0 && (
            <button className="btn btn-success" onClick={doBulkApprove}>
              <Check size={14} /> Approve {selected.size} selected
            </button>
          )}
          <button className="btn btn-ghost" onClick={loadRecords}>
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card" style={{ padding: 14, marginBottom: 16, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <FilterSelect name="scope" options={SCOPES} />
        <FilterSelect name="source_type" options={SOURCES} />
        <FilterSelect name="status" options={STATUSES} />
        <FilterSelect name="category" options={CATEGORIES} />
        <input type="date" value={filters.date_from} onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} style={{ width: 140 }} placeholder="Date from" />
        <input type="date" value={filters.date_to} onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} style={{ width: 140 }} placeholder="Date to" />
        <button className="btn btn-ghost btn-sm" onClick={() => setFilters({ scope: '', source_type: '', status: '', category: '', date_from: '', date_to: '' })}>
          Clear
        </button>
      </div>

      {/* Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center' }}><div className="loader" /></div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 36 }}>
                    <input type="checkbox" checked={selected.size === records.length && records.length > 0}
                      onChange={selectAll} style={{ width: 14 }} />
                  </th>
                  <th>Date</th>
                  <th>Source</th>
                  <th>Scope</th>
                  <th>Category</th>
                  <th>Qty (Normalized)</th>
                  <th>CO₂e</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {records.length === 0 ? (
                  <tr><td colSpan={10} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>No records found</td></tr>
                ) : records.map(r => (
                  <tr key={r.id} className={r.status === 'FLAGGED' ? 'flagged-row' : ''}>
                    <td>
                      <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelect(r.id)} style={{ width: 14 }} />
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>{r.activity_date || '—'}</td>
                    <td><span className={`badge badge-${r.source_type?.toLowerCase()}`}>{r.source_type}</span></td>
                    <td><span className={`scope-${r.scope}`} style={{ fontWeight: 600, fontSize: 12 }}>S{r.scope}</span></td>
                    <td style={{ fontSize: 12 }}>{r.category}</td>
                    <td className="mono" style={{ fontSize: 12 }}>
                      {r.quantity_normalized != null ? `${r.quantity_normalized.toFixed(2)} ${r.quantity_normalized_unit}` : '—'}
                    </td>
                    <td className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{formatCO2(r.co2e_kg)}</td>
                    <td style={{ fontSize: 12, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.location || '—'}</td>
                    <td><StatusBadge status={r.status} size="sm" /></td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="btn btn-ghost btn-sm" title="View" onClick={() => navigate(`/records/${r.id}`)}>
                          ↗
                        </button>
                        {r.status !== 'APPROVED' && !r.is_locked && (
                          <button className="btn btn-success btn-sm" title="Approve" onClick={() => doApprove(r.id)}
                            disabled={acting === r.id}>
                            <Check size={11} />
                          </button>
                        )}
                        {r.status !== 'REJECTED' && !r.is_locked && (
                          <button className="btn btn-danger btn-sm" title="Reject"
                            onClick={() => { setActionModal({ id: r.id, type: 'reject' }); setActionReason(''); }}>
                            <X size={11} />
                          </button>
                        )}
                        {r.status !== 'FLAGGED' && !r.is_locked && (
                          <button className="btn btn-warning btn-sm" title="Flag"
                            onClick={() => { setActionModal({ id: r.id, type: 'flag' }); setActionReason(''); }}>
                            <Flag size={11} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Action modal */}
      {actionModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }}>
          <div className="glass-card" style={{ padding: 24, width: 400 }}>
            <h3 style={{ marginBottom: 12, textTransform: 'capitalize' }}>
              {actionModal.type} Record
            </h3>
            <textarea
              value={actionReason}
              onChange={e => setActionReason(e.target.value)}
              placeholder={`Reason for ${actionModal.type}...`}
              rows={3}
              style={{ marginBottom: 14 }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button className={`btn ${actionModal.type === 'reject' ? 'btn-danger' : 'btn-warning'}`}
                style={{ flex: 1 }} onClick={doAction} disabled={!actionReason.trim()}>
                Confirm {actionModal.type}
              </button>
              <button className="btn btn-ghost" onClick={() => setActionModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
