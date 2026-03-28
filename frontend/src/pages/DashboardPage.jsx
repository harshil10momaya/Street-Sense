import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { AlertTriangle, CheckCircle, Clock, TrendingUp, Activity } from 'lucide-react';
import { fetchDashboardStats, fetchComplaints } from '../services/api';
import { StatCard, Spinner, SeverityBadge, StatusBadge, IssueTypeBadge } from '../components/shared/UIComponents';
import ComplaintMap from '../components/shared/ComplaintMap';

const PIE_COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#22c55e'];

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchDashboardStats(),
      fetchComplaints({ perPage: 50 }),
    ]).then(([s, c]) => {
      setStats(s);
      setRecent(c.complaints || []);
    }).catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  const typeData = stats?.by_type
    ? Object.entries(stats.by_type).map(([name, value]) => ({ name, value }))
    : [];

  const statusData = stats?.by_status
    ? Object.entries(stats.by_status).map(([name, value]) => ({ name: name.replace('_', ' '), value }))
    : [];

  const openCount = stats?.by_status?.open || 0;
  const resolvedCount = stats?.by_status?.resolved || 0;
  const highCount = stats?.by_severity?.high || 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold font-display">Dashboard</h1>
        <p className="text-gray-500 mt-1">Real-time road monitoring overview</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Issues" value={stats?.total || 0} icon={Activity} color="text-blue-400" />
        <StatCard label="Open" value={openCount} icon={Clock} color="text-amber-400" />
        <StatCard label="Resolved" value={resolvedCount} icon={CheckCircle} color="text-green-400" />
        <StatCard label="High Severity" value={highCount} icon={AlertTriangle} color="text-red-400" />
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* By Type */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4">Issues by Type</h3>
          {typeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4}>
                  {typeData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-600 text-sm text-center py-8">No data yet</p>}
          <div className="flex flex-wrap gap-3 mt-2 justify-center">
            {typeData.map((d, i) => (
              <span key={d.name} className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className="w-2.5 h-2.5 rounded-sm" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                {d.name}: {d.value}
              </span>
            ))}
          </div>
        </div>

        {/* By Status */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4">Issues by Status</h3>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={statusData}>
                <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="value" fill="#16a34a" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-600 text-sm text-center py-8">No data yet</p>}
        </div>
      </div>

      {/* Map */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-medium text-gray-400 mb-4">Issue Locations</h3>
        <ComplaintMap complaints={recent} height="400px" />
      </div>

      {/* Recent Issues */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-medium text-gray-400 mb-4">Recent Reports</h3>
        <div className="space-y-2">
          {recent.slice(0, 8).map(c => (
            <div key={c.id} className="flex items-center justify-between py-2.5 border-b border-gray-800/30 last:border-0">
              <div className="flex items-center gap-3">
                <IssueTypeBadge type={c.issue_type} />
                <span className="text-xs text-gray-500">{c.address?.slice(0, 35) || `${c.latitude?.toFixed(3)}, ${c.longitude?.toFixed(3)}`}</span>
              </div>
              <div className="flex items-center gap-2">
                <SeverityBadge severity={c.severity} />
                <StatusBadge status={c.status} />
              </div>
            </div>
          ))}
          {recent.length === 0 && <p className="text-gray-600 text-sm text-center py-4">No complaints yet. Upload an image to get started.</p>}
        </div>
      </div>
    </div>
  );
}
