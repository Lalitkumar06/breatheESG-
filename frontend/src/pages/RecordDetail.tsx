import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, X, Flag, Edit3, Lock, Clock } from 'lucide-react';
import { recordsAPI } from '../api/client';
import StatusBadge from '../components/StatusBadge';

function JsonViewer({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="json-viewer">
      {JSON.stringify(data, null, 2)}
    </div>
  );
}

function TimelineItem({ action, user, timestamp, notes, before, after }: any) {
  const [expanded, setExpanded] = useState(false);
  const colorMap: Record<string, string> = {
    APPROVED: '#00e676', REJECTED: '#ff5252', FLAGGED: '#b388ff',
    EDITED: '#82b1ff', BULK_APPROVED: '#00e676',
  };
  const color = colorMap[action] || '#8ba3c7';

  return (
    <div className="timeline-item">
      <div className="timeline-dot" style={{ borderColor: color, color, background: `${color}18`, fontSize: 10 }}>
        {action[0]}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
          <span style={{ fontWeight: 600, color, fontSize: 13 }}>{action}</span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>by {user}</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {new Date(timestamp).toLocaleString()}
          </span>
        </div>
        {notes && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{notes}</div>}
        {(before || after) && (
          <button onClick={() => setExpanded(!expanded)}
            style={{ fontSize: 11, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            {expanded ? 'Hide diff ▲' : 'Show diff ▼'}
          </button>
        )}
        {expanded && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
            <div><div style={{ fontSize: 11, color: '#ff5252', marginBottom: 4 }}>Before</div><JsonViewer data={before || {}} /></div>
            <div><div style={{ fontSize: 11, color: '#00e676', marginBottom: 4 }}>After</div><JsonViewer data={after || {}} /></div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function RecordDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [record, setRecord] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<any>({});
  const [modal, setModal] = useState<{ type: 'reject' | 'flag' } | null>(null);
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => {
    if (!id) return;
    Promise.all([recordsAPI.detail(id), recordsAPI.history(id)])
      .then(([r, h]) => {
        setRecord(r.data);
        setHistory(h.data);
        setEditForm({ quantity: r.data.quantity, quantity_unit: r.data.quantity_unit, activity_date: r.data.activity_date });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const doApprove = async () => {
    setSaving(true);
    await recordsAPI.approve(id!).catch(console.error);
    setSaving(false);
    load();
  };

  const doAction = async () => {
    setSaving(true);
    if (modal?.type === 'reject') await recordsAPI.reject(id!, reason).catch(console.error);
    if (modal?.type === 'flag') await recordsAPI.flag(id!, reason).catch(console.error);
    setSaving(false);
    setModal(null);
    setReason('');
    load();
  };

  const doSave = async () => {
    setSaving(true);
    await recordsAPI.update(id!, editForm).catch(console.error);
    setSaving(false);
    setEditing(false);
    load();
  };

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><div className="loader" style={{ width: 40, height: 40 }} /></div>;
  if (!record) return <div className="alert alert-error" style={{ margin: 24 }}>Record not found</div>;

  const fields = [
    { label: 'Source', value: <span className={`badge badge-${record.source_type?.toLowerCase()}`}>{record.source_type}</span> },
    { label: 'Scope', value: <span className={`scope-${record.scope}`} style={{ fontWeight: 700 }}>{record.scope_label}</span> },
    { label: 'Category', value: record.category },
    { label: 'Activity Date', value: record.activity_date },
    { label: 'Period', value: record.period_start ? `${record.period_start} → ${record.period_end}` : '—' },
    { label: 'Quantity (Original)', value: `${record.quantity} ${record.quantity_unit}` },
    { label: 'Quantity (Normalized)', value: <span className="mono">{record.quantity_normalized?.toFixed(4)} {record.quantity_normalized_unit}</span> },
    { label: 'Emission Factor', value: <span className="mono">{record.emission_factor} {record.emission_factor_unit}</span> },
    { label: 'CO₂e', value: <span className="mono" style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent-green)' }}>{record.co2e_kg?.toFixed(4)} kg</span> },
    { label: 'Location', value: record.location || '—' },
    { label: 'Vendor', value: record.vendor || '—' },
    { label: 'Description', value: record.description || '—' },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1100 }} className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)}><ArrowLeft size={14} /></button>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Record Detail</h1>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{id}</div>
        </div>
        <StatusBadge status={record.status} />
        {record.is_locked && (
          <div className="badge" style={{ background: 'rgba(138,180,248,0.1)', color: '#8ab4f8', border: '1px solid rgba(138,180,248,0.2)' }}>
            <Lock size={10} /> Locked
          </div>
        )}
      </div>

      {record.flag_reason && (
        <div className="alert alert-warning" style={{ marginBottom: 16 }}>
          <Flag size={14} /> <strong>Flag reason:</strong> {record.flag_reason}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 16 }}>
        {/* Left: Record fields */}
        <div>
          <div className="glass-card" style={{ padding: 20, marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Record Data</h3>
              {!record.is_locked && (
                <button className="btn btn-ghost btn-sm" onClick={() => setEditing(!editing)}>
                  <Edit3 size={12} /> {editing ? 'Cancel' : 'Edit'}
                </button>
              )}
            </div>

            {editing ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Quantity</label>
                  <input type="number" value={editForm.quantity} onChange={e => setEditForm((f: any) => ({ ...f, quantity: parseFloat(e.target.value) }))} />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Unit</label>
                  <input value={editForm.quantity_unit} onChange={e => setEditForm((f: any) => ({ ...f, quantity_unit: e.target.value }))} />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Activity Date</label>
                  <input type="date" value={editForm.activity_date} onChange={e => setEditForm((f: any) => ({ ...f, activity_date: e.target.value }))} />
                </div>
                <button className="btn btn-primary" onClick={doSave} disabled={saving}>
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '10px 20px', alignItems: 'start' }}>
                {fields.map(f => (
                  <React.Fragment key={f.label}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase', paddingTop: 2 }}>{f.label}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{f.value}</div>
                  </React.Fragment>
                ))}
              </div>
            )}
          </div>

          {/* Raw Data */}
          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>Raw Source Data</h3>
            <JsonViewer data={record.raw_data} />
          </div>
        </div>

        {/* Right: Actions + History */}
        <div>
          {/* Actions */}
          {!record.is_locked && (
            <div className="glass-card" style={{ padding: 16, marginBottom: 16 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>Actions</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {record.status !== 'APPROVED' && (
                  <button className="btn btn-success" style={{ justifyContent: 'center' }} onClick={doApprove} disabled={saving}>
                    <Check size={14} /> Approve Record
                  </button>
                )}
                {record.status !== 'REJECTED' && (
                  <button className="btn btn-danger" style={{ justifyContent: 'center' }} onClick={() => { setModal({ type: 'reject' }); setReason(''); }}>
                    <X size={14} /> Reject Record
                  </button>
                )}
                {record.status !== 'FLAGGED' && (
                  <button className="btn btn-warning" style={{ justifyContent: 'center' }} onClick={() => { setModal({ type: 'flag' }); setReason(''); }}>
                    <Flag size={14} /> Flag for Review
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Audit Timeline */}
          <div className="glass-card" style={{ padding: 16 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 14 }}>
              <Clock size={13} style={{ display: 'inline', marginRight: 6 }} />
              Audit Trail
            </h3>
            {history?.audit_trail?.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No actions recorded yet.</p>
            ) : history?.audit_trail?.map((log: any) => (
              <TimelineItem key={log.id}
                action={log.action}
                user={log.performed_by_username}
                timestamp={log.timestamp}
                notes={log.notes}
                before={log.before_state}
                after={log.after_state}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Modal */}
      {modal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="glass-card" style={{ padding: 24, width: 400 }}>
            <h3 style={{ marginBottom: 12, textTransform: 'capitalize' }}>{modal.type} Record</h3>
            <textarea value={reason} onChange={e => setReason(e.target.value)}
              placeholder={`Reason for ${modal.type}...`} rows={3} style={{ marginBottom: 14 }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button className={`btn ${modal.type === 'reject' ? 'btn-danger' : 'btn-warning'}`} style={{ flex: 1 }}
                onClick={doAction} disabled={!reason.trim() || saving}>
                Confirm {modal.type}
              </button>
              <button className="btn btn-ghost" onClick={() => setModal(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
