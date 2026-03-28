import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { TrendingUp, Clock, MapPin, Building2, BarChart3 } from 'lucide-react';
import { Spinner, StatCard } from '../components/shared/UIComponents';
import api from '../services/api';

const COLORS = { pothole: '#ef4444', crack: '#f59e0b', manhole: '#06b6d4', garbage: '#22c55e' };
const SEV_COLORS = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' };

const tooltipStyle = { background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 };

export default function AnalyticsPage() {
  const [trends, setTrends] = useState([]);
  const [resolution, setResolution] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [distribution, setDistribution] = useState({});
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/analytics/daily-trends?days=30').then(r => r.data),
      api.get('/analytics/resolution-time').then(r => r.data),
      api.get('/analytics/hotspots?limit=10').then(r => r.data),
      api.get('/analytics/severity-distribution').then(r => r.data),
      api.get('/analytics/department-performance').then(r => r.data),
    ]).then(([t, r, h, s, d]) => {
      setTrends(t.trends || []);
      setResolution(r.resolution_times || []);
      setHotspots(h.hotspots || []);
      setDistribution(s.distribution || {});
      setDepartments(d.departments || []);
    }).catch(err => console.error('Analytics error:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  // Compute summary stats
  const totalComplaints = trends.reduce((s, d) => s + d.total, 0);
  const todayCount = trends.length > 0 ? trends[trends.length - 1].total : 0;
  const avgPerDay = trends.length > 0 ? Math.round(totalComplaints / trends.length) : 0;
  const peakDay = trends.reduce((max, d) => d.total > max.total ? d : max, { total: 0 });

  // Severity pie data
  const sevPieData = Object.entries(distribution).flatMap(([type, sevs]) =>
    Object.entries(sevs).filter(([k]) => k !== 'total').map(([sev, count]) => ({
      name: `${type} (${sev})`, value: count, fill: SEV_COLORS[sev],
    }))
  ).filter(d => d.value > 0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold font-display flex items-center gap-2">
          <BarChart3 className="text-brand-400" size={24} /> Analytics
        </h1>
        <p className="text-gray-500 mt-1">Insights from complaint data (last 30 days)</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Last 30 Days" value={totalComplaints} icon={TrendingUp} color="text-blue-400" />
        <StatCard label="Today" value={todayCount} icon={TrendingUp} color="text-green-400" />
        <StatCard label="Avg / Day" value={avgPerDay} icon={Clock} color="text-amber-400" />
        <StatCard label="Peak Day" value={peakDay.total} icon={TrendingUp} color="text-red-400"
          trend={peakDay.date || ''} />
      </div>

      {/* Daily Trends Line Chart */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-medium text-gray-400 mb-4">Daily Complaint Trends</h3>
        {trends.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false}
                tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="pothole" stroke={COLORS.pothole} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="crack" stroke={COLORS.crack} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="manhole" stroke={COLORS.manhole} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="garbage" stroke={COLORS.garbage} strokeWidth={2} dot={false} />
              <Legend />
            </LineChart>
          </ResponsiveContainer>
        ) : <p className="text-gray-600 text-center py-8">No trend data yet</p>}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Severity Distribution */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4">Severity by Type</h3>
          {Object.keys(distribution).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(distribution).map(([type, sevs]) => (
                <div key={type}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-300">{type}</span>
                    <span className="text-xs text-gray-600">{sevs.total} total</span>
                  </div>
                  <div className="flex h-4 rounded-full overflow-hidden bg-gray-800">
                    {['low', 'medium', 'high'].map(sev => {
                      const pct = sevs.total > 0 ? (sevs[sev] / sevs.total * 100) : 0;
                      return pct > 0 ? (
                        <div key={sev} style={{ width: `${pct}%`, background: SEV_COLORS[sev] }}
                          className="transition-all" title={`${sev}: ${sevs[sev]}`} />
                      ) : null;
                    })}
                  </div>
                  <div className="flex gap-3 mt-1">
                    {['low', 'medium', 'high'].map(sev => (
                      <span key={sev} className="text-[10px] text-gray-600">
                        <span className="inline-block w-2 h-2 rounded-sm mr-1" style={{ background: SEV_COLORS[sev] }} />
                        {sev}: {sevs[sev]}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : <p className="text-gray-600 text-center py-8">No data</p>}
        </div>

        {/* Resolution Time */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4 flex items-center gap-2">
            <Clock size={14} /> Avg Resolution Time (hours)
          </h3>
          {resolution.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={resolution}>
                <XAxis dataKey="issue_type" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="avg_hours" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-600 text-center py-8">No resolved complaints yet</p>}
        </div>
      </div>

      {/* Hotspots & Department Performance side by side */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Hotspot Areas */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4 flex items-center gap-2">
            <MapPin size={14} /> Hotspot Areas
          </h3>
          {hotspots.length > 0 ? (
            <div className="space-y-2">
              {hotspots.map((h, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800/30 last:border-0">
                  <div>
                    <span className="text-sm text-gray-300">{h.ward}</span>
                    <span className="block text-[10px] text-gray-600">{h.zone}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-semibold text-gray-200">{h.count}</span>
                    <span className="block text-[10px] text-gray-600">avg sev: {h.avg_severity.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : <p className="text-gray-600 text-center py-8">No location data</p>}
        </div>

        {/* Department Performance */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-medium text-gray-400 mb-4 flex items-center gap-2">
            <Building2 size={14} /> Department Performance
          </h3>
          {departments.length > 0 ? (
            <div className="space-y-3">
              {departments.map((d, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-300 truncate max-w-[200px]">{d.department}</span>
                    <span className="text-xs text-gray-500">{d.resolved}/{d.total} resolved</span>
                  </div>
                  <div className="flex h-2.5 rounded-full overflow-hidden bg-gray-800">
                    <div
                      style={{ width: `${d.resolution_rate}%` }}
                      className="bg-brand-500 rounded-full transition-all"
                    />
                  </div>
                  <span className="text-[10px] text-gray-600">{d.resolution_rate}% resolution rate</span>
                </div>
              ))}
            </div>
          ) : <p className="text-gray-600 text-center py-8">No department data</p>}
        </div>
      </div>
    </div>
  );
}
