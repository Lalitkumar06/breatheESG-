import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.username, form.password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Login failed. Check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-primary)',
      backgroundImage: 'radial-gradient(ellipse at 20% 50%, rgba(0,230,118,0.05) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(41,121,255,0.08) 0%, transparent 50%)',
    }}>
      <div style={{ width: '100%', maxWidth: 400, padding: '0 16px' }}>
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16, margin: '0 auto 14px',
            background: 'linear-gradient(135deg, #00e676 0%, #2979ff 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 32px rgba(0,230,118,0.3)',
          }}>
            <Leaf size={24} color="#fff" />
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.5 }}>Breathe ESG</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            Carbon Accounting & Review Platform
          </p>
        </div>

        <form onSubmit={handleSubmit} className="glass-card" style={{ padding: 28 }}>
          <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: 20 }}>Sign In</h2>

          {error && (
            <div className="alert alert-error" style={{ marginBottom: 16, fontSize: 12 }}>{error}</div>
          )}

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Username</label>
            <input
              id="username"
              type="text"
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              placeholder="e.g. admin"
              required
              autoFocus
            />
          </div>

          <div style={{ marginBottom: 20, position: 'relative' }}>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Password</label>
            <input
              id="password"
              type={showPass ? 'text' : 'password'}
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              placeholder="••••••••"
              required
              style={{ paddingRight: 40 }}
            />
            <button type="button" onClick={() => setShowPass(!showPass)}
              style={{ position: 'absolute', right: 10, top: 30, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
              {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>

          <button className="btn btn-primary" type="submit" style={{ width: '100%', justifyContent: 'center', padding: 12 }} disabled={loading}>
            {loading ? <span className="loader" style={{ width: 14, height: 14 }} /> : 'Sign In'}
          </button>

          <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Demo credentials:</div>
            {[
              ['admin', 'admin123', 'Superuser'],
              ['acme_analyst', 'analyst123', 'ACME Corp'],
            ].map(([u, p, t]) => (
              <div key={u} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>
                <span className="mono">{u} / {p}</span>
                <span style={{ color: 'var(--text-muted)' }}>{t}</span>
              </div>
            ))}
          </div>
        </form>
      </div>
    </div>
  );
}
