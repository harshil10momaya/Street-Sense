import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import Navbar from './components/shared/Navbar';
import { Spinner } from './components/shared/UIComponents';
import DashboardPage from './pages/DashboardPage';
import MapPage from './pages/MapPage';
import UploadPage from './pages/UploadPage';
import AuthorityPage from './pages/AuthorityPage';
import AnalyticsPage from './pages/AnalyticsPage';
import LiveDetectionPage from './pages/LiveDetectionPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnlyRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <Spinner />;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
}

function AppLayout() {
  const { isAuthenticated } = useAuth();

  return (
    <>
      {isAuthenticated && <Navbar />}
      <main className={isAuthenticated ? 'pt-20 pb-12 px-4 sm:px-6 max-w-7xl mx-auto' : ''}>
        <Routes>
          {/* Public auth pages */}
          <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
          <Route path="/signup" element={<PublicOnlyRoute><SignupPage /></PublicOnlyRoute>} />

          {/* Protected pages */}
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/map" element={<ProtectedRoute><MapPage /></ProtectedRoute>} />
          <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
          <Route path="/authority" element={<ProtectedRoute><AuthorityPage /></ProtectedRoute>} />
          <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="/live" element={<ProtectedRoute><LiveDetectionPage /></ProtectedRoute>} />

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen bg-gray-950">
          <AppLayout />
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
