import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Map, Shield, Upload, BarChart3, Activity, Bell, X, Check, LogOut, User } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useAuth } from '../../hooks/useAuth';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: BarChart3 },
  { path: '/map', label: 'Map', icon: Map },
  { path: '/upload', label: 'Report', icon: Upload },
  { path: '/authority', label: 'Authority', icon: Shield },
];

const SEVERITY_COLORS = {
  low: 'border-l-green-500',
  medium: 'border-l-amber-500',
  high: 'border-l-red-500',
  info: 'border-l-blue-500',
};

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const dropdownRef = useRef(null);

  // Fetch notifications
  const fetchNotifs = async () => {
    try {
      const res = await fetch('/api/v1/notifications/?limit=20');
      const data = await res.json();
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (e) {
      // silently fail
    }
  };

  // Poll every 15 seconds
  useEffect(() => {
    fetchNotifs();
    const interval = setInterval(fetchNotifs, 15000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowNotifs(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const markRead = async (id) => {
    try {
      await fetch(`/api/v1/notifications/${id}/read`, { method: 'POST' });
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      // silently fail
    }
  };

  const markAllRead = async () => {
    for (const n of notifications.filter(n => !n.read)) {
      await markRead(n.id);
    }
  };

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

          {/* Nav Links + Notifications */}
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

            {/* Notification Bell */}
            <div className="relative ml-2" ref={dropdownRef}>
              <button
                onClick={() => { setShowNotifs(!showNotifs); if (!showNotifs) fetchNotifs(); }}
                className="relative p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 transition-all"
              >
                <Bell size={18} />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-5 h-5 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center animate-pulse">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              {/* Dropdown */}
              {showNotifs && (
                <div className="absolute right-0 top-12 w-96 max-h-[480px] bg-gray-900 border border-gray-800 rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-50">
                  {/* Header */}
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
                    <h3 className="text-sm font-semibold font-display text-gray-200">Notifications</h3>
                    <div className="flex items-center gap-2">
                      {unreadCount > 0 && (
                        <button
                          onClick={markAllRead}
                          className="text-[11px] text-brand-400 hover:text-brand-300 flex items-center gap-1"
                        >
                          <Check size={12} /> Mark all read
                        </button>
                      )}
                      <button onClick={() => setShowNotifs(false)} className="text-gray-600 hover:text-gray-400">
                        <X size={16} />
                      </button>
                    </div>
                  </div>

                  {/* Notification List */}
                  <div className="overflow-y-auto max-h-[400px]">
                    {notifications.length === 0 ? (
                      <div className="py-12 text-center text-gray-600 text-sm">
                        No notifications yet
                      </div>
                    ) : (
                      notifications.map(n => (
                        <div
                          key={n.id}
                          onClick={() => !n.read && markRead(n.id)}
                          className={`px-4 py-3 border-b border-gray-800/40 border-l-4 cursor-pointer transition-colors
                            ${SEVERITY_COLORS[n.severity] || SEVERITY_COLORS.info}
                            ${n.read ? 'opacity-50 bg-transparent' : 'bg-gray-800/20 hover:bg-gray-800/40'}`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm font-medium truncate ${n.read ? 'text-gray-500' : 'text-gray-200'}`}>
                                {n.title}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5 truncate">{n.message}</p>
                              <p className="text-[10px] text-gray-700 mt-1">
                                {n.created_at ? formatDistanceToNow(new Date(n.created_at), { addSuffix: true }) : ''}
                              </p>
                            </div>
                            {!n.read && (
                              <span className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 shrink-0" />
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* User Menu */}
            <div className="flex items-center gap-2 ml-3 pl-3 border-l border-gray-800">
              <div className="hidden sm:flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-brand-600/20 flex items-center justify-center">
                  <User size={14} className="text-brand-400" />
                </div>
                <div className="text-xs">
                  <p className="text-gray-300 font-medium leading-tight">{user?.full_name?.split(' ')[0]}</p>
                  <p className="text-gray-600 leading-tight">{user?.role}</p>
                </div>
              </div>
              <button
                onClick={() => { logout(); navigate('/login'); }}
                className="p-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-gray-800/50 transition-all"
                title="Sign out"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
