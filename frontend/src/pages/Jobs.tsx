import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import { jobsAPI } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { useNavigate } from 'react-router-dom';

export default function Jobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const navigate = useNavigate();

  useEffect(() => {
    jobsAPI.list()
      .then(res => setJobs(res.data.results || res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: string) => {
    const next = new Set(expanded);
    next.has(id) ? next.delete(id) : next.add(id);
    setExpanded(next);
  };

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><div className="loader" style={{ width: 40, height: 40 }} /></div>;

  return (
    <div style={{ padding: 24, maxWidth: 1000 }} className="animate-fade-in">
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Ingestion Jobs</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>{jobs.length} jobs total</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {jobs.map(job => (
          <div key={job.id} className="glass-card" style={{ overflow: 'hidden' }}>
            {/* Job header */}
            <div
              style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}
              onClick={() => toggle(job.id)}
            >
              <span style={{ color: 'var(--text-muted)' }}>
                {expanded.has(job.id) ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {job.filename}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {new Date(job.uploaded_at).toLocaleString()} · by {job.uploaded_by_username}
                </div>
              </div>
              <span className={`badge badge-${job.source_type?.toLowerCase()}`}>{job.source_type}</span>
              <StatusBadge status={job.status} size="sm" />
              <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
                <span style={{ color: 'var(--text-muted)' }}>{job.row_count} <span style={{ color: 'var(--text-muted)' }}>rows</span></span>
                {job.error_count > 0 && (
                  <span style={{ color: 'var(--accent-red)' }}>
                    <AlertTriangle size={11} style={{ display: 'inline', marginRight: 3 }} />{job.error_count} errors
                  </span>
                )}
              </div>
            </div>

            {/* Expanded: record summary + errors */}
            {expanded.has(job.id) && (
              <div style={{ borderTop: '1px solid var(--border)', padding: '14px 16px', background: 'var(--bg-secondary)' }}>
                {/* Record summary */}
                <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
                  {Object.entries(job.record_summary || {}).map(([key, count]) => (
                    <div key={key} style={{ background: 'var(--bg-card)', borderRadius: 8, padding: '8px 14px', minWidth: 80 }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: 0.5 }}>{key}</div>
                      <div className="mono" style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{String(count)}</div>
                    </div>
                  ))}
                </div>

                <button className="btn btn-primary btn-sm" style={{ marginBottom: 14 }}
                  onClick={() => navigate(`/review?job_id=${job.id}`)}>
                  View Records →
                </button>

                {/* Error list */}
                {job.error_details?.length > 0 && (
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#ff8a80', marginBottom: 8 }}>
                      Ingestion Errors ({job.error_details.length})
                    </div>
                    <div style={{ maxHeight: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {job.error_details.map((e: any, i: number) => (
                        <div key={i} style={{
                          fontSize: 11, padding: '5px 10px',
                          background: 'rgba(255,82,82,0.06)', borderRadius: 5,
                          borderLeft: '3px solid var(--accent-red)',
                          color: 'var(--text-secondary)', fontFamily: 'monospace',
                        }}>
                          <span style={{ color: '#ff5252' }}>Row {e.row}:</span> {e.error}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {job.processing_log && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 12, color: '#ff5252', marginBottom: 4 }}>Pipeline Error Log</div>
                    <div className="json-viewer" style={{ maxHeight: 120, color: '#ff8a80' }}>{job.processing_log}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
