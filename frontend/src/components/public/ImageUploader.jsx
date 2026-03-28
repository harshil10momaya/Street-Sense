import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, MapPin, Loader2, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { uploadImage } from '../../services/api';
import { SeverityBadge, IssueTypeBadge } from '../shared/UIComponents';

export default function ImageUploader() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      const f = accepted[0];
      setFile(f);
      setPreview(URL.createObjectURL(f));
      setResult(null);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
  });

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
      },
      () => setError('Could not detect location. Enter manually.'),
    );
  };

  const handleSubmit = async () => {
    if (!file) { setError('Select an image'); return; }
    if (!latitude || !longitude) { setError('Location required'); return; }

    setLoading(true);
    setError(null);
    try {
      const data = await uploadImage(file, parseFloat(latitude), parseFloat(longitude));
      setResult(data);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Result View */}
      {result && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="text-green-400" size={24} />
              <h3 className="text-lg font-bold font-display">Analysis Complete</h3>
            </div>
            <button onClick={reset} className="text-gray-500 hover:text-gray-300">
              <X size={20} />
            </button>
          </div>

          <p className="text-sm text-gray-400">
            {result.detections?.length || 0} issue(s) detected in {result.processing_time_ms?.toFixed(0)}ms
          </p>

          {/* Annotated Image */}
          {result.annotated_image_url && (
            <img src={result.annotated_image_url} alt="Annotated" className="w-full rounded-xl border border-gray-800" />
          )}

          {/* Depth Map */}
          {result.depth_map_url && (
            <div>
              <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Depth Map (MiDaS)</p>
              <img src={result.depth_map_url} alt="Depth" className="w-full rounded-xl border border-gray-800" />
            </div>
          )}

          {/* Detections */}
          <div className="space-y-3">
            {result.detections?.map((det, i) => (
              <div key={i} className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <IssueTypeBadge type={det.issue_type} />
                  <span className="text-sm text-gray-400">conf: {(det.confidence * 100).toFixed(1)}%</span>
                </div>
                <SeverityBadge severity={det.severity} />
              </div>
            ))}
          </div>

          <button onClick={reset} className="w-full py-3 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium transition-colors">
            Upload Another
          </button>
        </div>
      )}

      {/* Upload Form */}
      {!result && (
        <div className="space-y-6">
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all
              ${isDragActive ? 'border-brand-500 bg-brand-500/5' : 'border-gray-700 hover:border-gray-600'}
              ${preview ? 'border-brand-500/50' : ''}`}
          >
            <input {...getInputProps()} />
            {preview ? (
              <div className="relative">
                <img src={preview} alt="Preview" className="max-h-64 mx-auto rounded-xl" />
                <p className="text-sm text-gray-400 mt-3">{file?.name}</p>
              </div>
            ) : (
              <div className="space-y-3">
                <Upload className="mx-auto text-gray-600" size={40} />
                <p className="text-gray-400 font-medium">Drop an image here or click to browse</p>
                <p className="text-xs text-gray-600">JPG, PNG, WebP up to 20MB</p>
              </div>
            )}
          </div>

          {/* Location */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-400">Location</label>
              <button onClick={detectLocation} className="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300">
                <MapPin size={12} /> Auto-detect
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="number" step="any" placeholder="Latitude"
                value={latitude} onChange={e => setLatitude(e.target.value)}
                className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-500 transition-colors"
              />
              <input
                type="number" step="any" placeholder="Longitude"
                value={longitude} onChange={e => setLongitude(e.target.value)}
                className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-brand-500 transition-colors"
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              <AlertTriangle size={16} /> {error}
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={loading || !file}
            className="w-full py-3.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-gray-800 disabled:text-gray-600 text-white font-semibold transition-all shadow-lg shadow-brand-600/20 disabled:shadow-none"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 size={18} className="animate-spin" /> Analyzing...
              </span>
            ) : (
              'Upload & Analyze'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
