import React, { useRef, useState, useEffect, useCallback } from 'react';
import {
  Video, VideoOff, Camera, AlertTriangle, Zap, Pause, Play,
  MapPin, Navigation, Save, Eye, Shield, CircleDot,
} from 'lucide-react';
import { SeverityBadge, IssueTypeBadge } from '../components/shared/UIComponents';
import api from '../services/api';

const SEVERITY_COLORS = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' };

export default function LiveDetectionPage() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const geoWatchRef = useRef(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [detections, setDetections] = useState([]);
  const [processTime, setProcessTime] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [error, setError] = useState('');
  const [captureInterval, setCaptureInterval] = useState(3000);

  // GPS State
  const [gpsLocation, setGpsLocation] = useState(null);
  const [gpsAccuracy, setGpsAccuracy] = useState(null);
  const [gpsSpeed, setGpsSpeed] = useState(null);
  const [gpsTracking, setGpsTracking] = useState(false);

  // Mode: 'preview' = detect only, 'report' = detect + auto-create complaints
  const [mode, setMode] = useState('preview');

  // Complaint log (recent auto-created complaints)
  const [complaintLog, setComplaintLog] = useState([]);
  const [totalReported, setTotalReported] = useState(0);

  // ---- GPS Tracking ----
  const startGpsTracking = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported by this browser');
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setGpsLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        });
        setGpsAccuracy(pos.coords.accuracy);
        setGpsSpeed(pos.coords.speed);
        setGpsTracking(true);
        setError('');
      },
      (err) => {
        if (err.code === 1) setError('Location access denied. Enable GPS permissions.');
        else if (err.code === 2) setError('GPS unavailable. Try moving outdoors.');
        else setError('GPS timeout. Retrying...');
        setGpsTracking(false);
      },
      {
        enableHighAccuracy: true,
        maximumAge: 5000,
        timeout: 10000,
      }
    );
    geoWatchRef.current = watchId;
  }, []);

  const stopGpsTracking = () => {
    if (geoWatchRef.current !== null) {
      navigator.geolocation.clearWatch(geoWatchRef.current);
      geoWatchRef.current = null;
    }
    setGpsTracking(false);
  };

  // ---- Camera ----
  const startCamera = async () => {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsStreaming(true);
      startGpsTracking();
    } catch (err) {
      if (err.name === 'NotAllowedError') setError('Camera access denied.');
      else if (err.name === 'NotFoundError') setError('No camera found.');
      else setError(`Camera error: ${err.message}`);
    }
  };

  const stopCamera = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null; }
    stopGpsTracking();
    setIsStreaming(false);
    setIsPaused(false);
    setDetections([]);
  };

  // ---- Frame Capture & Detection ----
  const getFrameBlob = async () => {
    if (!videoRef.current || !canvasRef.current) return null;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0) return null;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.85));
  };

  const captureAndDetect = useCallback(async () => {
    if (isPaused) return;
    const blob = await getFrameBlob();
    if (!blob) return;

    const formData = new FormData();
    formData.append('file', blob, 'frame.jpg');

    try {
      let res;
      if (mode === 'report' && gpsLocation) {
        // Auto-report mode: detect + geo-tag + save complaints
        formData.append('latitude', gpsLocation.lat);
        formData.append('longitude', gpsLocation.lng);
        res = await api.post('/live/frame-report', formData);

        if (res.data.complaints_created > 0) {
          const newEntries = res.data.detections.map((det, i) => ({
            id: res.data.complaint_ids?.[i] || Date.now() + i,
            type: det.issue_type,
            severity: det.severity,
            confidence: det.confidence,
            lat: gpsLocation.lat,
            lng: gpsLocation.lng,
            time: new Date().toLocaleTimeString(),
          }));
          setComplaintLog(prev => [...newEntries, ...prev].slice(0, 50));
          setTotalReported(prev => prev + res.data.complaints_created);
        }
      } else {
        // Preview mode: detect only
        res = await api.post('/live/frame', formData);
      }

      setDetections(res.data.detections || []);
      setProcessTime(res.data.processing_time_ms || 0);
      setFrameCount(prev => prev + 1);
      drawOverlay(res.data.detections || []);
    } catch (err) {
      console.warn('Frame error:', err.message);
    }
  }, [isPaused, mode, gpsLocation]);

  // ---- Manual Photo Capture ----
  const capturePhoto = async () => {
    if (!gpsLocation) { setError('GPS required for photo capture. Wait for GPS lock.'); return; }

    const blob = await getFrameBlob();
    if (!blob) return;

    const formData = new FormData();
    formData.append('file', blob, 'capture.jpg');
    formData.append('latitude', gpsLocation.lat);
    formData.append('longitude', gpsLocation.lng);

    try {
      const res = await api.post('/live/capture', formData);
      if (res.data.complaints_created > 0) {
        const newEntries = res.data.detections.map((det, i) => ({
          id: res.data.complaint_ids?.[i] || Date.now() + i,
          type: det.issue_type,
          severity: det.severity,
          confidence: det.confidence,
          lat: gpsLocation.lat,
          lng: gpsLocation.lng,
          time: new Date().toLocaleTimeString(),
          isCapture: true,
        }));
        setComplaintLog(prev => [...newEntries, ...prev].slice(0, 50));
        setTotalReported(prev => prev + res.data.complaints_created);
      }
      setDetections(res.data.detections || []);
      drawOverlay(res.data.detections || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Capture failed');
    }
  };

  // ---- Draw Detection Overlay ----
  const drawOverlay = (dets) => {
    const overlay = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!overlay || !video) return;
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    dets.forEach(det => {
      const { x, y, w, h } = det.bbox;
      const color = SEVERITY_COLORS[det.severity] || '#3b82f6';

      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.shadowColor = color;
      ctx.shadowBlur = 8;
      ctx.strokeRect(x, y, w, h);
      ctx.shadowBlur = 0;

      const label = `${det.issue_type} ${(det.confidence * 100).toFixed(0)}% [${det.severity}]`;
      ctx.font = 'bold 14px sans-serif';
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = color;
      ctx.fillRect(x, y - 24, tw + 12, 24);
      ctx.fillStyle = '#fff';
      ctx.fillText(label, x + 6, y - 7);
    });
  };

  // ---- Detection Loop ----
  useEffect(() => {
    if (isStreaming && !isPaused) {
      intervalRef.current = setInterval(captureAndDetect, captureInterval);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isStreaming, isPaused, captureAndDetect, captureInterval]);

  useEffect(() => { return () => stopCamera(); }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Video className="text-brand-400" size={24} /> Live Detection
          </h1>
          <p className="text-gray-500 mt-1">Real-time road monitoring with GPS tracking</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Mode Toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-700">
            <button onClick={() => setMode('preview')}
              className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1.5 transition-colors
                ${mode === 'preview' ? 'bg-blue-600/20 text-blue-400' : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
              <Eye size={12} /> Preview
            </button>
            <button onClick={() => setMode('report')}
              className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1.5 transition-colors
                ${mode === 'report' ? 'bg-red-600/20 text-red-400' : 'bg-gray-800 text-gray-500 hover:text-gray-300'}`}>
              <Shield size={12} /> Auto-Report
            </button>
          </div>

          <select value={captureInterval} onChange={e => setCaptureInterval(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-300">
            <option value={2000}>0.5 fps</option>
            <option value={3000}>0.3 fps</option>
            <option value={5000}>0.2 fps</option>
          </select>

          {!isStreaming ? (
            <button onClick={startCamera}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium">
              <Video size={16} /> Start
            </button>
          ) : (
            <>
              <button onClick={() => setIsPaused(!isPaused)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm">
                {isPaused ? <Play size={14} /> : <Pause size={14} />}
              </button>
              <button onClick={capturePhoto}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 text-sm font-medium"
                title="Capture photo and save complaint">
                <Camera size={14} /> Capture
              </button>
              <button onClick={stopCamera}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm">
                <VideoOff size={14} /> Stop
              </button>
            </>
          )}
        </div>
      </div>

      {/* Mode info banner */}
      {mode === 'report' && isStreaming && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <CircleDot size={16} className="animate-pulse" />
          <span className="font-medium">Auto-Report Active</span>
          <span className="text-red-400/70">-- Every detection is automatically geo-tagged and saved as a complaint</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Video Feed */}
        <div className="lg:col-span-2">
          <div className="relative bg-gray-900 rounded-2xl overflow-hidden border border-gray-800" style={{ aspectRatio: '16/9' }}>
            <video ref={videoRef} autoPlay playsInline muted className="absolute inset-0 w-full h-full object-cover" />
            <canvas ref={overlayCanvasRef} className="absolute inset-0 w-full h-full object-cover pointer-events-none" />
            <canvas ref={canvasRef} className="hidden" />

            {!isStreaming && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600">
                <Camera size={48} className="mb-3" />
                <p className="text-sm">Click Start to begin live detection</p>
                <p className="text-xs text-gray-700 mt-1">Camera + GPS will be activated</p>
              </div>
            )}

            {/* Status overlay */}
            {isStreaming && (
              <>
                <div className="absolute top-3 left-3 flex items-center gap-2">
                  <span className="flex items-center gap-1.5 px-2 py-1 rounded bg-black/70 text-xs font-mono">
                    <span className={`w-2 h-2 rounded-full ${isPaused ? 'bg-amber-500' : 'bg-red-500 animate-pulse'}`} />
                    {isPaused ? 'PAUSED' : mode === 'report' ? 'REPORTING' : 'LIVE'}
                  </span>
                  <span className="px-2 py-1 rounded bg-black/70 text-xs font-mono text-gray-400">
                    {processTime.toFixed(0)}ms
                  </span>
                </div>

                {/* GPS overlay */}
                <div className="absolute bottom-3 left-3 flex items-center gap-2">
                  <span className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono
                    ${gpsTracking ? 'bg-green-900/70 text-green-400' : 'bg-red-900/70 text-red-400'}`}>
                    <Navigation size={10} />
                    {gpsTracking
                      ? `${gpsLocation?.lat.toFixed(5)}, ${gpsLocation?.lng.toFixed(5)}`
                      : 'GPS searching...'}
                  </span>
                  {gpsAccuracy && (
                    <span className="px-2 py-1 rounded bg-black/70 text-[10px] font-mono text-gray-500">
                      +/-{gpsAccuracy.toFixed(0)}m
                    </span>
                  )}
                  {gpsSpeed !== null && gpsSpeed > 0 && (
                    <span className="px-2 py-1 rounded bg-black/70 text-[10px] font-mono text-gray-500">
                      {(gpsSpeed * 3.6).toFixed(0)} km/h
                    </span>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div className="space-y-4">
          {/* Session Stats */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2 mb-3">
              <Zap size={14} /> Session
            </h3>
            <div className="grid grid-cols-2 gap-2 text-center">
              <StatBox label="Frames" value={frameCount} />
              <StatBox label="Reported" value={totalReported} color="text-red-400" />
              <StatBox label="ms/frame" value={processTime.toFixed(0)} />
              <StatBox label="Current" value={detections.length} />
            </div>
          </div>

          {/* Current Detections */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <h3 className="text-sm font-medium text-gray-400 mb-3">Current Frame</h3>
            {detections.length === 0 ? (
              <p className="text-gray-600 text-xs text-center py-3">
                {isStreaming ? 'No issues in current frame' : 'Start camera to begin'}
              </p>
            ) : (
              <div className="space-y-2">
                {detections.map((det, i) => (
                  <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-800/30 last:border-0">
                    <IssueTypeBadge type={det.issue_type} />
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">{(det.confidence * 100).toFixed(0)}%</span>
                      <SeverityBadge severity={det.severity} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Complaint Log (auto-reported) */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 max-h-64 overflow-y-auto">
            <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
              <Save size={14} /> Reported ({totalReported})
            </h3>
            {complaintLog.length === 0 ? (
              <p className="text-gray-600 text-xs text-center py-3">
                {mode === 'report' ? 'Detections will auto-save here' : 'Switch to Auto-Report mode'}
              </p>
            ) : (
              <div className="space-y-1.5">
                {complaintLog.map((c, i) => (
                  <div key={c.id || i} className="flex items-center justify-between text-xs py-1 border-b border-gray-800/20 last:border-0">
                    <div className="flex items-center gap-2">
                      {c.isCapture && <Camera size={10} className="text-amber-400" />}
                      <IssueTypeBadge type={c.type} />
                    </div>
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={c.severity} />
                      <span className="text-gray-700 text-[10px]">{c.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatBox({ label, value, color = 'text-gray-200' }) {
  return (
    <div className="bg-gray-800/40 rounded-lg p-2">
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-[10px] text-gray-600">{label}</p>
    </div>
  );
}
