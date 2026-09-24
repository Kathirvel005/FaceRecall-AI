"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { API_BASE_URL, WS_BASE_URL, fetchSystemInfo, fetchPersons, fetchEvents, toggleCamera, togglePipeline } from "../services/api";
import { RecognitionFrameSummary, SystemInfo, Person, RecognitionEvent } from "../types";

export default function DashboardPage() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [persons, setPersons] = useState<Person[]>([]);
  const [events, setEvents] = useState<RecognitionEvent[]>([]);
  const [frameSummary, setFrameSummary] = useState<RecognitionFrameSummary | null>(null);
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  // Poll system info & persons list
  useEffect(() => {
    const loadData = async () => {
      try {
        const [sys, per, evts] = await Promise.all([
          fetchSystemInfo(),
          fetchPersons(),
          fetchEvents(8)
        ]);
        setSystemInfo(sys);
        setPersons(per);
        setEvents(evts);
      } catch (err) {
        console.error("Dashboard initial fetch error:", err);
      }
    };
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Connect WebSocket for live face count and frame metrics
  useEffect(() => {
    let ws: WebSocket;
    const connectWs = () => {
      ws = new WebSocket(`${WS_BASE_URL}/ws/recognition`);
      wsRef.current = ws;

      ws.onopen = () => setIsWsConnected(true);
      ws.onclose = () => {
        setIsWsConnected(false);
        setTimeout(connectWs, 3000);
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.frame_id) {
            setFrameSummary(data);
          }
        } catch {}
      };
    };

    connectWs();
    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Real-time canvas overlay: Green for Known, Red for Unknown
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frameSummary || !frameSummary.faces) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const srcW = frameSummary.frame_width || 1280;
    const srcH = frameSummary.frame_height || 720;
    const srcAspect = srcW / srcH;
    const boxAspect = rect.width / rect.height;

    let renderW = rect.width;
    let renderH = rect.height;
    let offsetX = 0;
    let offsetY = 0;

    if (boxAspect > srcAspect) {
      renderW = rect.height * srcAspect;
      offsetX = (rect.width - renderW) / 2;
    } else {
      renderH = rect.width / srcAspect;
      offsetY = (rect.height - renderH) / 2;
    }

    const scaleX = renderW / srcW;
    const scaleY = renderH / srcH;

    frameSummary.faces.forEach((face) => {
      const [origX1, origY1, origX2, origY2] = face.bbox;
      const x1 = offsetX + origX1 * scaleX;
      const y1 = offsetY + origY1 * scaleY;
      const x2 = offsetX + origX2 * scaleX;
      const y2 = offsetY + origY2 * scaleY;
      const w = x2 - x1;
      const h = y2 - y1;

      const isKnown = face.status === "KNOWN";
      const strokeColor = isKnown ? "#22c55e" : "#ef4444";
      const fillColor = isKnown ? "rgba(34, 197, 94, 0.18)" : "rgba(239, 68, 68, 0.18)";
      const badgeBg = isKnown ? "#15803d" : "#b91c1c";

      ctx.save();
      ctx.shadowColor = strokeColor;
      ctx.shadowBlur = 6;
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.5;
      ctx.fillStyle = fillColor;

      ctx.beginPath();
      ctx.roundRect(x1, y1, w, h, 6);
      ctx.fill();
      ctx.stroke();
      ctx.restore();

      if (face.landmarks) {
        ctx.fillStyle = strokeColor;
        face.landmarks.forEach(([lx, ly]) => {
          ctx.beginPath();
          ctx.arc(offsetX + lx * scaleX, offsetY + ly * scaleY, 2.5, 0, 2 * Math.PI);
          ctx.fill();
        });
      }

      const badgeText = isKnown
        ? `${face.name} | ${Math.round(face.similarity * 100)}%`
        : "UNKNOWN";

      ctx.font = "bold 11px sans-serif";
      const textWidth = ctx.measureText(badgeText).width;
      const badgeH = 26;
      const badgeW = textWidth + 14;
      const badgeY = Math.max(0, y1 - badgeH - 3);

      ctx.fillStyle = badgeBg;
      ctx.beginPath();
      ctx.roundRect(x1, badgeY, badgeW, badgeH, 4);
      ctx.fill();

      ctx.fillStyle = "#ffffff";
      ctx.fillText(badgeText, x1 + 7, badgeY + 17);
    });
  }, [frameSummary]);

  const handleToggleCamera = async (start: boolean) => {
    setIsProcessing(true);
    try {
      await toggleCamera(start);
      const sys = await fetchSystemInfo();
      setSystemInfo(sys);
    } catch (e) {
      alert("Failed to toggle camera: " + e);
    } finally {
      setIsProcessing(false);
    }
  };

  const isCamRunning = systemInfo?.camera_status?.is_running ?? false;


  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Classroom Attendance & Identity Monitor</h2>
          <p className="text-sm text-gray-400">
            Real-time multi-face detection, ArcFace verification, and persistent identity tracking
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => handleToggleCamera(!isCamRunning)}
            disabled={isProcessing}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm ${
              isCamRunning
                ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30"
                : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30"
            }`}
          >
            {isCamRunning ? "⏹ Stop Camera" : "▶ Start Camera"}
          </button>
          <Link
            href="/recognition"
            className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white rounded-lg text-sm font-medium shadow-md shadow-cyan-900/20 transition-all flex items-center space-x-2"
          >
            <span>🎥 Open Live Recognition UI</span>
          </Link>
        </div>
      </div>

      {/* Real-time Metric Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {/* Metric 1 */}
        <div className="glass-card p-4 rounded-xl border border-gray-800">
          <p className="text-xs font-medium text-gray-400">Active Faces</p>
          <p className="text-2xl font-bold text-white mt-1">
            {frameSummary?.face_count ?? 0}
          </p>
          <span className="text-[11px] text-cyan-400">Current frame</span>
        </div>

        {/* Metric 2 */}
        <div className="glass-card p-4 rounded-xl border border-gray-800">
          <p className="text-xs font-medium text-gray-400">Recognized</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">
            {frameSummary?.known_count ?? 0}
          </p>
          <span className="text-[11px] text-emerald-500/80">Identified Students</span>
        </div>

        {/* Metric 3 */}
        <div className="glass-card p-4 rounded-xl border border-gray-800">
          <p className="text-xs font-medium text-gray-400">Unknown</p>
          <p className="text-2xl font-bold text-rose-400 mt-1">
            {frameSummary?.unknown_count ?? 0}
          </p>
          <span className="text-[11px] text-rose-500/80">Unregistered Faces</span>
        </div>

        {/* Metric 4 */}
        <div className="glass-card p-4 rounded-xl border border-gray-800">
          <p className="text-xs font-medium text-gray-400">FPS / Latency</p>
          <p className="text-2xl font-bold text-white mt-1">
            {frameSummary?.fps ? frameSummary.fps.toFixed(1) : "30.0"}
          </p>
          <span className="text-[11px] text-gray-400">
            {frameSummary?.inference_latency_ms ? `${frameSummary.inference_latency_ms} ms` : "0 ms"}
          </span>
        </div>

        {/* Metric 5 */}
        <div className="glass-card p-4 rounded-xl border border-gray-800">
          <p className="text-xs font-medium text-gray-400">Registered</p>
          <p className="text-2xl font-bold text-white mt-1">
            {persons.length}
          </p>
          <span className="text-[11px] text-gray-400">Total Enrolled</span>
        </div>

        {/* Metric 6 */}
        <div className="glass-card p-4 rounded-xl border border-gray-800">
          <p className="text-xs font-medium text-gray-400">FAISS Index</p>
          <p className="text-2xl font-bold text-cyan-400 mt-1">
            {systemInfo?.vector_store_count ?? 0}
          </p>
          <span className="text-[11px] text-cyan-500/80">512-D Vectors</span>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Live Camera Preview */}
        <div className="lg:col-span-2 glass-card rounded-xl border border-gray-800 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-gray-800/80 flex items-center justify-between bg-[#0e1424]">
            <div className="flex items-center space-x-2">
              <span className={`w-2.5 h-2.5 rounded-full ${isWsConnected ? "bg-emerald-400 animate-pulse" : "bg-rose-500"}`} />
              <h3 className="text-sm font-semibold text-white">Live Classroom Camera Feed</h3>
            </div>
            <span className="text-xs text-gray-400 font-mono">
              {systemInfo?.camera_status?.resolution ?? "1280x720"}
            </span>
          </div>

          <div className="relative bg-black flex items-center justify-center min-h-[360px] aspect-video">
            {isCamRunning ? (
              <>
                <img
                  ref={imgRef}
                  src={`${API_BASE_URL}/camera/stream`}
                  alt="Live Camera Feed"
                  className="w-full h-full object-contain"
                />
                <canvas
                  ref={canvasRef}
                  className="absolute inset-0 pointer-events-none w-full h-full"
                />
              </>
            ) : (
              <div className="text-center p-8">
                <span className="text-4xl">📷</span>
                <p className="text-gray-400 text-sm mt-2">Camera is currently stopped</p>
                <button
                  onClick={() => handleToggleCamera(true)}
                  className="mt-3 px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-medium transition"
                >
                  Start Camera Feed
                </button>
              </div>
            )}

            {/* In-Frame Live Overlay Badge */}
            {isCamRunning && frameSummary && (
              <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 text-xs flex items-center space-x-3">
                <span className="text-emerald-400 font-medium">● Known: {frameSummary.known_count}</span>
                <span className="text-rose-400 font-medium">● Unknown: {frameSummary.unknown_count}</span>
                <span className="text-gray-300 font-mono">{frameSummary.inference_latency_ms} ms</span>
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Recent Recognition Events */}
        <div className="glass-card rounded-xl border border-gray-800 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-gray-800">
              <h3 className="text-sm font-semibold text-white">Recent Recognition Events</h3>
              <Link href="/events" className="text-xs text-cyan-400 hover:underline">
                View All
              </Link>
            </div>

            <div className="mt-3 space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {events.length === 0 ? (
                <p className="text-xs text-gray-500 text-center py-8">No recognition events logged yet.</p>
              ) : (
                events.map((evt) => (
                  <div
                    key={evt.id}
                    className="p-2.5 rounded-lg bg-gray-900/60 border border-gray-800 flex items-center justify-between text-xs"
                  >
                    <div>
                      <p className="font-medium text-white">{evt.name}</p>
                      <p className="text-[11px] text-gray-400">
                        {evt.student_id ? `ID: ${evt.student_id}` : `Track #${evt.track_id}`}
                      </p>
                    </div>
                    <div className="text-right">
                      <span
                        className={`inline-block px-2 py-0.5 rounded font-mono font-medium ${
                          evt.status === "KNOWN"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {evt.status} ({Math.round(evt.similarity * 100)}%)
                      </span>
                      <p className="text-[10px] text-gray-500 mt-1">
                        {new Date(evt.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Quick Enrolled Directory Preview */}
          <div className="pt-4 border-t border-gray-800">
            <Link
              href="/persons/register"
              className="w-full py-2.5 bg-gray-800/80 hover:bg-gray-800 text-white rounded-lg text-xs font-medium border border-gray-700/60 flex items-center justify-center space-x-2 transition"
            >
              <span>➕ Enroll New Student</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
