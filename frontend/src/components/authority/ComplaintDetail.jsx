import React, { useState, useEffect } from 'react';
import { X, ChevronRight, Clock, User, Building2 } from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { SeverityBadge, StatusBadge, IssueTypeBadge } from '../shared/UIComponents';
import { updateComplaintStatus, fetchComplaintHistory } from '../../services/api';

const TRANSITIONS = {
  open: ['assigned'],
  assigned: ['in_progress', 'open'],
  in_progress: ['resolved', 'assigned'],
  resolved: ['verified', 'in_progress'],
  verified: [],
};

export default function ComplaintDetail({ complaint, onClose, onUpdate }) {
  const [history, setHistory] = useState([]);
  const [updating, setUpdating] = useState(false);
  const [notes, setNotes] = useState('');

  const c = complaint;
  if (!c) return null;

  const currentStatus = c.status;
  const allowedNext = TRANSITIONS[currentStatus] || [];

  useEffect(() => {
    if (c.id) {
      fetchComplaintHistory(c.id).then(setHistory).catch(() => {});
    }
  }, [c.id]);

  const handleStatusUpdate = async (newStatus) => {
    setUpdating(true);
    try {
      const updated = await updateComplaintStatus(c.id, newStatus, null, null, notes || undefined);
      onUpdate?.(updated);
      setNotes('');
      fetchComplaintHistory(c.id).then(setHistory).catch(() => {});
    } catch (err) {
      alert(err.response?.data?.detail || 'Update failed');
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-lg h-full bg-gray-900 border-l border-gray-800 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900/95 backdrop-blur border-b border-gray-800 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <IssueTypeBadge type={c.issue_type} />
            <SeverityBadge severity={c.severity} />
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X size={20} /></button>
        </div>

        <div className="p-5 space-y-6">
          {/* Images */}
          {c.annotated_image_path && (
            <img src={c.annotated_image_path} alt="Annotated" className="w-full rounded-xl border border-gray-800" />
          )}
          {c.image_path && !c.annotated_image_path && (
            <img src={c.image_path} alt="Original" className="w-full rounded-xl border border-gray-800" />
          )}

          {/* Info Grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <InfoRow icon={Clock} label="Status" value={<StatusBadge status={c.status} />} />
            <InfoRow label="Confidence" value={`${(c.confidence * 100).toFixed(1)}%`} />
            <InfoRow label="Severity Score" value={c.severity_score?.toFixed(4)} />
            <InfoRow label="Depth" value={c.depth_value?.toFixed(4) || 'N/A'} />
            <InfoRow icon={Building2} label="Department" value={c.department || 'Unassigned'} />
            <InfoRow icon={User} label="Assigned To" value={c.assigned_to || 'Unassigned'} />
          </div>

          {/* Location */}
          <div className="bg-gray-800/40 rounded-xl p-4 space-y-2 text-sm">
            <p className="text-gray-500 text-xs uppercase tracking-wider font-medium">Location</p>
            <p className="text-gray-300">{c.address || 'Address not available'}</p>
            <div className="flex gap-4 text-xs text-gray-500">
              <span>{c.ward || 'Unknown ward'}</span>
              <span>{c.zone || 'Unknown zone'}</span>
            </div>
            <p className="text-xs font-mono text-gray-600">{c.latitude?.toFixed(6)}, {c.longitude?.toFixed(6)}</p>
          </div>

          {/* Status Transitions */}
          {allowedNext.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">Update Status</p>
              <textarea
                placeholder="Notes (optional)..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="w-full bg-gray-800/60 border border-gray-700 rounded-xl px-4 py-2.5 text-sm resize-none h-20 focus:outline-none focus:border-brand-500"
              />
              <div className="flex gap-2">
                {allowedNext.map(s => (
                  <button
                    key={s}
                    onClick={() => handleStatusUpdate(s)}
                    disabled={updating}
                    className="flex items-center gap-1 px-4 py-2 rounded-lg bg-brand-600/20 text-brand-400 hover:bg-brand-600/30 text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    <ChevronRight size={14} />
                    {s.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* History */}
          {history.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">History</p>
              <div className="space-y-2">
                {history.map((h, i) => (
                  <div key={h.id || i} className="flex items-start gap-3 text-xs">
                    <div className="w-2 h-2 rounded-full bg-gray-600 mt-1.5 shrink-0" />
                    <div>
                      <span className="text-gray-400">
                        {h.previous_status || 'created'} <ChevronRight size={10} className="inline" /> {h.new_status}
                      </span>
                      {h.notes && <p className="text-gray-600 mt-0.5">{h.notes}</p>}
                      <p className="text-gray-700 mt-0.5">
                        {h.created_at ? format(new Date(h.created_at), 'MMM d, yyyy HH:mm') : ''}
                        {h.changed_by && ` by ${h.changed_by}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="text-xs text-gray-600 space-y-1 pt-4 border-t border-gray-800">
            <p>Created: {c.created_at ? format(new Date(c.created_at), 'PPpp') : '-'}</p>
            <p>Updated: {c.updated_at ? format(new Date(c.updated_at), 'PPpp') : '-'}</p>
            {c.resolved_at && <p>Resolved: {format(new Date(c.resolved_at), 'PPpp')}</p>}
            <p className="font-mono text-gray-700">ID: {c.id}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, value }) {
  return (
    <div className="bg-gray-800/30 rounded-lg p-3">
      <p className="text-gray-600 text-xs mb-1 flex items-center gap-1">
        {Icon && <Icon size={11} />} {label}
      </p>
      <div className="text-gray-300">{value}</div>
    </div>
  );
}
