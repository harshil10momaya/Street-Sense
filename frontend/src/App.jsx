import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/shared/Navbar';
import DashboardPage from './pages/DashboardPage';
import MapPage from './pages/MapPage';
import UploadPage from './pages/UploadPage';
import AuthorityPage from './pages/AuthorityPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950">
        <Navbar />
        <main className="pt-20 pb-12 px-4 sm:px-6 max-w-7xl mx-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/authority" element={<AuthorityPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
