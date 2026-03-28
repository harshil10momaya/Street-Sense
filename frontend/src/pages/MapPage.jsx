import React, { useEffect, useState } from 'react';
import { fetchComplaints } from '../services/api';
import ComplaintMap from '../components/shared/ComplaintMap';
import ComplaintDetail from '../components/authority/ComplaintDetail';
import { Spinner } from '../components/shared/UIComponents';

export default function MapPage() {
  const [complaints, setComplaints] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    fetchComplaints({ perPage: 100 })
      .then(data => setComplaints(data.complaints || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-display">Map View</h1>
          <p className="text-gray-500 mt-1">{complaints.length} issues on map</p>
        </div>
      </div>

      <div className="rounded-2xl overflow-hidden border border-gray-800">
        <ComplaintMap
          complaints={complaints}
          height="calc(100vh - 200px)"
          onMarkerClick={setSelected}
        />
      </div>

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
