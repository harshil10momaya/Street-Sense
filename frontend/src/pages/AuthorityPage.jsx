import React, { useEffect, useState, useCallback } from 'react';
import { Shield, Filter, RefreshCw } from 'lucide-react';
import { fetchComplaints } from '../services/api';
import ComplaintTable from '../components/authority/ComplaintTable';
import ComplaintDetail from '../components/authority/ComplaintDetail';
import { Spinner } from '../components/shared/UIComponents';

const STATUS_OPTIONS = ['', 'open', 'assigned', 'in_progress', 'resolved', 'verified'];
const SEVERITY_OPTIONS = ['', 'low', 'medium', 'high'];
const TYPE_OPTIONS = ['', 'pothole', 'crack', 'manhole', 'garbage'];

export default function AuthorityPage() {
  const [complaints, setComplaints] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterType, setFilterType] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    fetchComplaints({
      page,
      perPage: 25,
      status: filterStatus || undefined,
      severity: filterSeverity || undefined,
      issueType: filterType || undefined,
    })
      .then(data => {
        setComplaints(data.complaints || []);
        setTotal(data.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, filterStatus, filterSeverity, filterType]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.ceil(total / 25);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="text-brand-400" size={24} />
          <div>
            <h1 className="text-2xl font-bold font-display">Authority Dashboard</h1>
            <p className="text-gray-500 text-sm">{total} complaint{total !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-4 bg-gray-900/50 border border-gray-800/50 rounded-xl">
        <Filter size={14} className="text-gray-500" />
        <select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none">
          <option value="">All Status</option>
          {STATUS_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <select value={filterSeverity} onChange={e => { setFilterSeverity(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none">
          <option value="">All Severity</option>
          {SEVERITY_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filterType} onChange={e => { setFilterType(e.target.value); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none">
          <option value="">All Types</option>
          {TYPE_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl overflow-hidden">
        {loading ? <Spinner /> : (
          <ComplaintTable complaints={complaints} onSelect={setSelected} />
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1.5 rounded-lg bg-gray-800 text-sm text-gray-400 hover:bg-gray-700 disabled:opacity-40">
            Prev
          </button>
          <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="px-3 py-1.5 rounded-lg bg-gray-800 text-sm text-gray-400 hover:bg-gray-700 disabled:opacity-40">
            Next
          </button>
        </div>
      )}

      {/* Detail Panel */}
      {selected && (
        <ComplaintDetail
          complaint={selected}
          onClose={() => setSelected(null)}
          onUpdate={(updated) => {
            setComplaints(prev => prev.map(c => c.id === updated.id ? updated : c));
            setSelected(updated);
          }}
        />
      )}
    </div>
  );
}
