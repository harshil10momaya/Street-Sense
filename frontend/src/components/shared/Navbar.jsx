import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Map, Shield, Upload, BarChart3, Activity } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: BarChart3 },
  { path: '/map', label: 'Map', icon: Map },
  { path: '/upload', label: 'Report', icon: Upload },
  { path: '/authority', label: 'Authority', icon: Shield },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-950/80 backdrop-blur-xl border-b border-gray-800/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-brand-600 flex items-center justify-center shadow-lg shadow-brand-600/20 group-hover:shadow-brand-600/40 transition-shadow">
              <Activity size={20} className="text-white" />
            </div>
            <div>
              <span className="text-lg font-bold font-display text-white tracking-tight">StreetSense</span>
              <span className="hidden sm:inline text-[10px] text-gray-500 ml-2 uppercase tracking-widest">AI Road Monitor</span>
            </div>
          </Link>

          {/* Nav Links */}
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map(({ path, label, icon: Icon }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all
                    ${active
                      ? 'bg-brand-600/15 text-brand-400'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                    }`}
                >
                  <Icon size={16} />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
