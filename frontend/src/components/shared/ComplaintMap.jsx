import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

const SEVERITY_COLORS = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' };
const ISSUE_ICONS = { pothole: '🕳', crack: '⚡', manhole: '⬛', garbage: '🗑' };

function createMarkerIcon(severity) {
  const color = SEVERITY_COLORS[severity] || '#3b82f6';
  return L.divIcon({
    className: '',
    html: `<div style="
      width:28px;height:28px;border-radius:50%;
      background:${color};border:3px solid ${color}44;
      box-shadow:0 0 12px ${color}66;
      display:flex;align-items:center;justify-content:center;
      font-size:12px;
    "></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
}

export default function ComplaintMap({ complaints = [], center = [13.0827, 80.2707], zoom = 12, height = '500px', onMarkerClick }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    if (mapInstanceRef.current) return;

    mapInstanceRef.current = L.map(mapRef.current, {
      center,
      zoom,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(mapInstanceRef.current);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current) return;

    // Clear old markers
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    // Add new markers
    complaints.forEach(c => {
      if (!c.latitude || !c.longitude) return;

      const icon = createMarkerIcon(c.severity);
      const marker = L.marker([c.latitude, c.longitude], { icon })
        .addTo(mapInstanceRef.current);

      const popup = `
        <div style="font-family:'IBM Plex Sans',sans-serif;min-width:180px;">
          <div style="font-weight:600;font-size:14px;margin-bottom:4px;">
            ${ISSUE_ICONS[c.issue_type] || ''} ${c.issue_type?.toUpperCase()}
          </div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:6px;">
            ${c.address || 'Location not available'}
          </div>
          <div style="display:flex;gap:8px;font-size:11px;">
            <span style="color:${SEVERITY_COLORS[c.severity]}">${c.severity?.toUpperCase()}</span>
            <span style="color:#94a3b8;">|</span>
            <span style="color:#94a3b8;">${c.status}</span>
          </div>
        </div>
      `;
      marker.bindPopup(popup);

      if (onMarkerClick) {
        marker.on('click', () => onMarkerClick(c));
      }

      markersRef.current.push(marker);
    });

    // Fit bounds if complaints exist
    if (complaints.length > 0) {
      const bounds = complaints
        .filter(c => c.latitude && c.longitude)
        .map(c => [c.latitude, c.longitude]);
      if (bounds.length > 0) {
        mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
      }
    }
  }, [complaints]);

  return <div ref={mapRef} style={{ height, width: '100%', borderRadius: '12px' }} />;
}
