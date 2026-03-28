import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { SeverityBadge, StatusBadge, IssueTypeBadge } from '../shared/UIComponents';

export default function ComplaintTable({ complaints = [], onSelect }) {
  if (complaints.length === 0) {
    return <p className="text-gray-500 text-center py-8">No complaints found.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-800/60">
            <th className="pb-3 pl-4 font-medium">Type</th>
            <th className="pb-3 font-medium">Location</th>
            <th className="pb-3 font-medium">Severity</th>
            <th className="pb-3 font-medium">Status</th>
            <th className="pb-3 font-medium">Department</th>
            <th className="pb-3 font-medium">Reported</th>
          </tr>
        </thead>
        <tbody>
          {complaints.map(c => (
            <tr
              key={c.id}
              onClick={() => onSelect?.(c)}
              className="border-b border-gray-800/30 hover:bg-gray-800/30 cursor-pointer transition-colors"
            >
              <td className="py-3 pl-4">
                <IssueTypeBadge type={c.issue_type} />
              </td>
              <td className="py-3">
                <span className="text-gray-300 text-xs">{c.address?.slice(0, 40) || `${c.latitude?.toFixed(4)}, ${c.longitude?.toFixed(4)}`}</span>
                {c.ward && <span className="block text-gray-600 text-[10px]">{c.ward}</span>}
              </td>
              <td className="py-3"><SeverityBadge severity={c.severity} /></td>
              <td className="py-3"><StatusBadge status={c.status} /></td>
              <td className="py-3 text-gray-500 text-xs">{c.department || '-'}</td>
              <td className="py-3 text-gray-500 text-xs">
                {c.created_at ? formatDistanceToNow(new Date(c.created_at), { addSuffix: true }) : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
