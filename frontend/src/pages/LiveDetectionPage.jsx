import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Video, VideoOff, Camera, AlertTriangle, Zap, Pause, Play } from 'lucide-react';
import { SeverityBadge, IssueTypeBadge } from '../components/shared/UIComponents';
import api from '../services/api';

export default function LiveDetectionPage() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [detections, setDetections] = useState([]);
  const [fps, setFps] = useState(0);
  const [processTime, setProcessTime] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [totalDetections, setTotalDetections] = useState(0);
  const [error, setError] = useState('');
  const [captureInterval, setCaptureInterval] = useState(2000); // ms between frames

  const SEVERITY_COLORS = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444' };
  const CLASS_COLORS = { pothole: '#ef4444', crack: '#f59e0b', manhole: '#06b6d4', garbage: '#22c55e' };

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
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Camera access denied. Please allow camera permissions.');
      } else if (err.name === 'NotFoundError') {
        setError('No camera found. Connect a webcam or dashcam.');
      } else {
        setError(`Camera error: ${err.message}`);
      }
    }
  };

  const stopCamera = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setIsStreaming(false);
    setIsPaused(false);
    setDetections([]);
  };

  const captureAndDetect = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || isPaused) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (video.videoWidth === 0) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    // Convert canvas to blob
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
    if (!blob) return;

    const formData = new FormData();
    formData.append('file', blob, 'frame.jpg');

    const start = performance.now();
    try {
      const res = await api.post('/live/frame', formData);
      const elapsed = performance.now() - start;

      setDetections(res.data.detections || []);
      setProcessTime(res.data.processing_time_ms || elapsed);
      setFps(Math.round(1000 / elapsed));
      setFrameCount(prev => prev + 1);
      setTotalDetections(prev => prev + (res.data.detections?.length || 0));

      // Draw detection overlay
      drawOverlay(res.data.detections || [], video.videoWidth, video.videoHeight);

    } catch (err) {
      // Don't stop on individual frame errors
      console.warn('Frame detection failed:', err.message);
    }
  }, [isPaused]);

  const drawOverlay = (dets, width, height) => {
    const overlay = overlayCanvasRef.current;
    if (!overlay) return;

    overlay.width = width;
    overlay.height = height;
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, width, height);

    dets.forEach(det => {
      const bbox = det.bbox;
      const x = bbox.x;
      const y = bbox.y;
      const w = bbox.w;
      const h = bbox.h;

      const color = SEVERITY_COLORS[det.severity] || '#3b82f6';

      // Box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x, y, w, h);

      // Label background
      const label = `${det.issue_type} ${(det.confidence * 100).toFixed(0)}% [${det.severity}]`;
      ctx.font = 'bold 14px sans-serif';
      const textWidth = ctx.measureText(label).width;

      ctx.fillStyle = color;
      ctx.fillRect(x, y - 22, textWidth + 10, 22);

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x + 5, y - 6);
    });
  };

  // Start/stop detection loop
  useEffect(() => {
    if (isStreaming && !isPaused) {
      intervalRef.current = setInterval(captureAndDetect, captureInterval);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isStreaming, isPaused, captureAndDetect, captureInterval]);

  // Cleanup on unmount
  useEffect(() => { return () => stopCamera(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Video className="text-brand-400" size={24} /> Live Detection
          </h1>
          <p className="text-gray-500 mt-1">Real-time road damage detection via camera</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Capture speed control */}
          <select
            value={captureInterval}
            onChange={e => setCaptureInterval(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-300"
          >
            <option value={1000}>1 fps</option>
            <option value={2000}>0.5 fps</option>
            <option value={3000}>0.3 fps</option>
            <option value={5000}>0.2 fps</option>
          </select>

          {!isStreaming ? (
            <button onClick={startCamera}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors">
              <Video size={16} /> Start Camera
            </button>
          ) : (
            <>
              <button onClick={() => setIsPaused(!isPaused)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors">
                {isPaused ? <Play size={14} /> : <Pause size={14} />}
                {isPaused ? 'Resume' : 'Pause'}
              </button>
              <button onClick={stopCamera}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm transition-colors">
                <VideoOff size={14} /> Stop
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {/* Video + Detection Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Video Feed */}
        <div className="lg:col-span-2">
          <div className="relative bg-gray-900 rounded-2xl overflow-hidden border border-gray-800"
            style={{ aspectRatio: '16/9' }}>
            <video ref={videoRef} autoPlay playsInline muted
              className="absolute inset-0 w-full h-full object-cover" />
            <canvas ref={overlayCanvasRef}
              className="absolute inset-0 w-full h-full object-cover pointer-events-none" />
            <canvas ref={canvasRef} className="hidden" />

            {!isStreaming && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600">
                <Camera size={48} className="mb-3" />
                <p className="text-sm">Click "Start Camera" to begin live detection</p>
                <p className="text-xs text-gray-700 mt-1">Supports webcam and USB dashcams</p>
              </div>
            )}

            {/* Live stats overlay */}
            {isStreaming && (
              <div className="absolute top-3 left-3 flex items-center gap-3">
                <span className="flex items-center gap-1.5 px-2 py-1 rounded bg-black/60 text-xs font-mono">
                  <span className={`w-2 h-2 rounded-full ${isPaused ? 'bg-amber-500' : 'bg-red-500 animate-pulse'}`} />
                  {isPaused ? 'PAUSED' : 'LIVE'}
                </span>
                <span className="px-2 py-1 rounded bg-black/60 text-xs font-mono text-gray-400">
                  {processTime.toFixed(0)}ms
                </span>
                <span className="px-2 py-1 rounded bg-black/60 text-xs font-mono text-gray-400">
                  F:{frameCount}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Detection Panel */}
        <div className="space-y-4">
          {/* Session Stats */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Zap size={14} /> Session Stats
            </h3>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="bg-gray-800/40 rounded-lg p-2">
                <p className="text-lg font-bold text-gray-200">{frameCount}</p>
                <p className="text-[10px] text-gray-600">Frames</p>
              </div>
              <div className="bg-gray-800/40 rounded-lg p-2">
                <p className="text-lg font-bold text-gray-200">{totalDetections}</p>
                <p className="text-[10px] text-gray-600">Detections</p>
              </div>
              <div className="bg-gray-800/40 rounded-lg p-2">
                <p className="text-lg font-bold text-gray-200">{processTime.toFixed(0)}</p>
                <p className="text-[10px] text-gray-600">ms / frame</p>
              </div>
              <div className="bg-gray-800/40 rounded-lg p-2">
                <p className="text-lg font-bold text-gray-200">{detections.length}</p>
                <p className="text-[10px] text-gray-600">Current</p>
              </div>
            </div>
          </div>

          {/* Current Detections */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <h3 className="text-sm font-medium text-gray-400 mb-3">Current Detections</h3>
            {detections.length === 0 ? (
              <p className="text-gray-600 text-xs text-center py-4">
                {isStreaming ? 'No issues detected in current frame' : 'Start camera to begin'}
              </p>
            ) : (
              <div className="space-y-2">
                {detections.map((det, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800/30 last:border-0">
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

          {/* Instructions */}
          <div className="bg-gray-800/30 rounded-xl p-4 text-xs text-gray-600 space-y-1">
            <p className="font-medium text-gray-500 mb-2">Tips:</p>
            <p>- Point camera at road surface for best results</p>
            <p>- Lower capture rate for slower connections</p>
            <p>- Works with USB dashcams and phone cameras</p>
            <p>- Detection boxes update each frame</p>
          </div>
        </div>
      </div>
    </div>
  );
}
