import React from 'react';

// ---- Severity Badge ----
export function SeverityBadge({ severity }) {
  const colors = {
    low: 'bg-green-500/20 text-green-400 border-green-500/30',
    medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    high: 'bg-red-500/20 text-red-400 border-red-500/30 severity-high',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[severity] || colors.low}`}>
      {severity?.toUpperCase()}
    </span>
  );
}

// ---- Status Badge ----
export function StatusBadge({ status }) {
  const colors = {
    open: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    assigned: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    in_progress: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    resolved: 'bg-green-500/20 text-green-400 border-green-500/30',
    verified: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  };
  const labels = {
    open: 'Open',
    assigned: 'Assigned',
    in_progress: 'In Progress',
    resolved: 'Resolved',
    verified: 'Verified',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[status] || colors.open}`}>
      {labels[status] || status}
    </span>
  );
}

// ---- Issue Type Badge ----
export function IssueTypeBadge({ type }) {
  const colors = {
    pothole: 'bg-red-500/15 text-red-400',
    crack: 'bg-orange-500/15 text-orange-400',
    manhole: 'bg-cyan-500/15 text-cyan-400',
    garbage: 'bg-green-500/15 text-green-400',
  };
  const icons = { pothole: '🕳', crack: '⚡', manhole: '⬛', garbage: '🗑' };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colors[type] || ''}`}>
      <span>{icons[type] || '?'}</span> {type}
    </span>
  );
}

// ---- Stat Card ----
export function StatCard({ label, value, icon: Icon, color = 'text-brand-400', trend }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-500 text-sm font-medium mb-1">{label}</p>
          <p className={`text-3xl font-bold font-display ${color}`}>{value}</p>
          {trend && <p className="text-xs text-gray-500 mt-1">{trend}</p>}
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-lg bg-gray-800/60 ${color}`}>
            <Icon size={22} />
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Empty State ----
export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && <Icon size={48} className="text-gray-600 mb-4" />}
      <h3 className="text-lg font-medium text-gray-400 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 max-w-md">{description}</p>
    </div>
  );
}

// ---- Loading Spinner ----
export function Spinner({ size = 'md' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' };
  return (
    <div className="flex items-center justify-center p-8">
      <div className={`${sizes[size]} border-2 border-gray-700 border-t-brand-500 rounded-full animate-spin`} />
    </div>
  );
}
