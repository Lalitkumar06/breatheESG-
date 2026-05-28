import { useState, useRef, useCallback, useEffect } from 'react';
import { Upload as UploadIcon, CheckCircle, XCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { jobsAPI } from '../api/client';
import StatusBadge from '../components/StatusBadge';

const SOURCE_TYPES = [
  { value: 'SAP',     label: 'SAP (Fuel & Procurement)',  hint: 'Tab-delimited or CSV with German headers', color: '#82b1ff' },
  { value: 'UTILITY', label: 'Utility (Electricity)',      hint: 'CSV with billing period columns',          color: '#69db7c' },
  { value: 'TRAVEL',  label: 'Corporate Travel',           hint: 'Concur/Navan-style CSV export',            color: '#ffd180' },
];

export default function UploadPage() {
  const [sourceType, setSourceType] = useState('SAP');
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [job, setJob] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll job status
  useEffect(() => {
    if (job?.id && job.status === 'PROCESSING' || job?.status === 'PENDING') {
      pollRef.current = setInterval(() => {
        jobsAPI.detail(job.id).then(res => {
          setJob(res.data);
          if (res.data.status === 'COMPLETE' || res.data.status === 'FAILED') {
            if (pollRef.current) clearInterval(pollRef.current);
          }
        });
      }, 2000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [job?.id, job?.status]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const res = await jobsAPI.upload(file, sourceType);
      setJob(res.data);
    } catch (e: any) {
      setError(e.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setJob(null);
    setError('');
    if (pollRef.current) clearInterval(pollRef.current);
  };

  return (
    <div style={{ padding: 24, maxWidth: 800 }} className="animate-fade-in">
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Upload Emissions Data</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 24 }}>
        Upload SAP, Utility, or Travel CSV files for ingestion and normalization.
      </p>

      {/* Source type selector */}
      <div className="glass-card" style={{ padding: 20, marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', display: 'block', marginBottom: 10 }}>
          Data Source Type
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
          {SOURCE_TYPES.map(st => (
            <button
              key={st.value}
              onClick={() => setSourceType(st.value)}
              style={{
                padding: '12px 14px',
                borderRadius: 10,
                border: `2px solid ${sourceType === st.value ? st.color : 'var(--border)'}`,
                background: sourceType === st.value ? `${st.color}18` : 'var(--bg-secondary)',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s',
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 600, color: sourceType === st.value ? st.color : 'var(--text-primary)', marginBottom: 4 }}>
                {st.label}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{st.hint}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      {!job && (
        <div
          className={`upload-zone glass-card ${dragging ? 'drag-over' : ''}`}
          style={{ marginBottom: 16 }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input ref={fileRef} type="file" accept=".csv,.tsv,.txt" hidden
            onChange={e => setFile(e.target.files?.[0] || null)} />
          <UploadIcon size={36} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
          {file ? (
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>{file.name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                {(file.size / 1024).toFixed(1)} KB
              </div>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 4 }}>
                Drop file here or click to browse
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>CSV, TSV up to 10MB</div>
            </div>
          )}
        </div>
      )}

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}><XCircle size={14} />{error}</div>}

      {/* Upload button */}
      {!job && (
        <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: 12 }}
          onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? <><span className="loader" style={{ width: 14, height: 14 }} /> Uploading...</> : <><UploadIcon size={14} /> Start Ingestion</>}
        </button>
      )}

      {/* Job status card */}
      {job && (
        <div className="glass-card animate-fade-in" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>{job.filename}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Job ID: {job.id?.slice(0, 8)}…</div>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <StatusBadge status={job.status} />
              {(job.status === 'PROCESSING' || job.status === 'PENDING') && (
                <RefreshCw size={14} style={{ color: 'var(--accent-blue)', animation: 'spin 1s linear infinite' }} />
              )}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'Rows Processed', value: job.row_count, color: 'var(--text-primary)' },
              { label: 'Successful', value: job.success_count, color: 'var(--accent-green)' },
              { label: 'Errors', value: job.error_count, color: job.error_count > 0 ? 'var(--accent-red)' : 'var(--text-muted)' },
            ].map(stat => (
              <div key={stat.label} style={{ background: 'var(--bg-secondary)', borderRadius: 8, padding: '10px 14px' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{stat.label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: stat.color }} className="mono">{stat.value ?? '—'}</div>
              </div>
            ))}
          </div>

          {/* Error details */}
          {job.error_details?.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--accent-red)', fontWeight: 600, marginBottom: 8 }}>
                <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4 }} />
                {job.error_details.length} errors encountered
              </div>
              <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                {job.error_details.map((e: any, i: number) => (
                  <div key={i} style={{
                    fontSize: 12, padding: '6px 10px', marginBottom: 4,
                    background: 'rgba(255,82,82,0.08)', borderRadius: 6,
                    borderLeft: '3px solid var(--accent-red)', color: 'var(--text-secondary)',
                  }}>
                    <span style={{ color: '#ff8a80' }}>Row {e.row}:</span> {e.error}
                  </div>
                ))}
              </div>
            </div>
          )}

          {job.status === 'COMPLETE' && (
            <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
              <a href="/review" className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>
                <CheckCircle size={14} /> View in Review Queue
              </a>
              <button className="btn btn-ghost" onClick={reset}>Upload Another</button>
            </div>
          )}
          {job.status === 'FAILED' && (
            <button className="btn btn-ghost" style={{ marginTop: 12, width: '100%', justifyContent: 'center' }} onClick={reset}>
              Try Again
            </button>
          )}
        </div>
      )}
    </div>
  );
}
