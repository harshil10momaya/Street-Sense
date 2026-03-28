import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus, AlertTriangle, Activity } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '', city: '', state: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 6) { setError('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      await signup(form);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gray-950 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-brand-600/20">
            <Activity size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold font-display text-white">Create Account</h1>
          <p className="text-gray-500 mt-1">Join StreetSense to report road issues</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900/60 border border-gray-800 rounded-2xl p-8 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Full Name *</label>
            <input
              type="text" required value={form.full_name} onChange={e => update('full_name', e.target.value)}
              placeholder="John Doe"
              className="w-full bg-gray-800/60 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Email *</label>
            <input
              type="email" required value={form.email} onChange={e => update('email', e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-gray-800/60 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Password *</label>
            <input
              type="password" required value={form.password} onChange={e => update('password', e.target.value)}
              placeholder="Min 6 characters"
              className="w-full bg-gray-800/60 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Phone</label>
            <input
              type="tel" value={form.phone} onChange={e => update('phone', e.target.value)}
              placeholder="+91 9876543210"
              className="w-full bg-gray-800/60 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">City</label>
              <input
                type="text" value={form.city} onChange={e => update('city', e.target.value)}
                placeholder="Chennai"
                className="w-full bg-gray-800/60 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">State</label>
              <input
                type="text" value={form.state} onChange={e => update('state', e.target.value)}
                placeholder="Tamil Nadu"
                className="w-full bg-gray-800/60 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-colors"
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              <AlertTriangle size={16} /> {error}
            </div>
          )}

          <button
            type="submit" disabled={loading}
            className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-gray-800 disabled:text-gray-600 text-white font-semibold transition-all shadow-lg shadow-brand-600/20 disabled:shadow-none"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>

          <p className="text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
