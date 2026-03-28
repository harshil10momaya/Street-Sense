import React from 'react';
import ImageUploader from '../components/public/ImageUploader';
import { Camera, Shield, Zap } from 'lucide-react';

export default function UploadPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-10">
      <div className="text-center">
        <h1 className="text-3xl font-bold font-display">Report a Road Issue</h1>
        <p className="text-gray-500 mt-2 max-w-lg mx-auto">
          Upload a photo and our AI will detect potholes, cracks, manholes, and garbage with depth-aware severity estimation.
        </p>
      </div>

      {/* Feature highlights */}
      <div className="grid grid-cols-3 gap-4 max-w-xl mx-auto">
        {[
          { icon: Camera, label: 'AI Detection', desc: 'YOLOv8 powered' },
          { icon: Zap, label: 'Depth Analysis', desc: 'MiDaS severity' },
          { icon: Shield, label: 'Auto-Routing', desc: 'Smart assignment' },
        ].map(({ icon: Icon, label, desc }) => (
          <div key={label} className="text-center p-4 rounded-xl bg-gray-900/40 border border-gray-800/50">
            <Icon size={20} className="mx-auto text-brand-400 mb-2" />
            <p className="text-xs font-medium text-gray-300">{label}</p>
            <p className="text-[10px] text-gray-600">{desc}</p>
          </div>
        ))}
      </div>

      {/* Upload Form */}
      <div className="bg-gray-900/40 border border-gray-800/50 rounded-2xl p-6 md:p-8">
        <ImageUploader />
      </div>
    </div>
  );
}
