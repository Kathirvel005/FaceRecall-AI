"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, WS_BASE_URL } from "../../services/api";
import { FaceRecognitionResult, RecognitionFrameSummary } from "../../types";

export default function LiveRecognitionPage() {
  const [frameSummary, setFrameSummary] = useState<RecognitionFrameSummary | null>(null);
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);
  const [canvasScale, setCanvasScale] = useState<{ x: number; y: number }>({ x: 1, y: 1 });
  const [selectedFace, setSelectedFace] = useState<FaceRecognitionResult | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket Connection
  useEffect(() => {
    let ws: WebSocket;
    const connect = () => {
      ws = new WebSocket(`${WS_BASE_URL}/ws/recognition`);
      wsRef.current = ws;

      ws.onopen = () => setIsWsConnected(true);
      ws.onclose = () => {
        setIsWsConnected(false);
        setTimeout(connect, 3000);
      };
      ws.onmessage = (event) => {
        try {
          const data: RecognitionFrameSummary = JSON.parse(event.data);
          if (data && data.faces) {
            setFrameSummary(data);
          }
        } catch {}
      };
    };

    connect();
    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Draw Bounding Boxes and Landmarks on Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !frameSummary) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = img.getBoundingClientRect();
    // Only resize canvas if dimensions actually changed to prevent high-frequency flickering
    if (Math.abs(canvas.width - rect.width) > 1 || Math.abs(canvas.height - rect.height) > 1) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Compute exact rendered image dimensions and letterbox offsets for object-contain
    const srcW = frameSummary.frame_width || 1280;
    const srcH = frameSummary.frame_height || 720;
    const srcAspect = srcW / srcH;
    const containerAspect = rect.width / rect.height;

    let renderW = rect.width;
    let renderH = rect.height;
    let offsetX = 0;
    let offsetY = 0;

    if (containerAspect > srcAspect) {
      // Letterbox bars on left/right
      renderW = rect.height * srcAspect;
      offsetX = (rect.width - renderW) / 2;
    } else {
      // Letterbox bars on top/bottom
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

      // Clear color scheme: KNOWN = Green, UNKNOWN = Red
      let strokeColor = "#ef4444"; // Red: UNKNOWN
      let fillColor = "rgba(239, 68, 68, 0.18)";
      let badgeBg = "#b91c1c";

      if (face.status === "KNOWN") {
        strokeColor = "#22c55e"; // Green: KNOWN
        fillColor = "rgba(34, 197, 94, 0.18)";
        badgeBg = "#15803d";
      }

      // 1. Draw Bounding Box with subtle glow
      ctx.save();
      ctx.shadowColor = strokeColor;
      ctx.shadowBlur = 6;
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.5;
      ctx.fillStyle = fillColor;

      // Rounded rectangle
      const radius = 6;
      ctx.beginPath();
      ctx.roundRect(x1, y1, w, h, radius);
      ctx.fill();
      ctx.stroke();
      ctx.restore();

      // 2. Draw 5 Facial Landmarks (subtle dots)
      if (face.landmarks) {
        ctx.fillStyle = strokeColor;
        face.landmarks.forEach(([lx, ly]) => {
          ctx.beginPath();
          ctx.arc(offsetX + lx * scaleX, offsetY + ly * scaleY, 2.5, 0, 2 * Math.PI);
          ctx.fill();
        });
      }

      // 3. Draw Top Information Badge
      const isKnown = face.status === "KNOWN";
      const badgeText = isKnown
        ? `${face.name} | ${Math.round(face.similarity * 100)}%`
        : "UNKNOWN";
      const subText = isKnown
        ? `Track #${face.track_id} · Q: ${(face.quality * 100).toFixed(0)}%`
        : `Unregistered · Track #${face.track_id}`;

      ctx.font = "bold 12px sans-serif";
      const textWidth = Math.max(ctx.measureText(badgeText).width, ctx.measureText(subText).width);
      const badgeH = 34;
      const badgeW = textWidth + 16;
      const badgeY = Math.max(0, y1 - badgeH - 4);

      ctx.fillStyle = badgeBg;
      ctx.beginPath();
      ctx.roundRect(x1, badgeY, badgeW, badgeH, 4);
      ctx.fill();

      // Text inside badge
      ctx.fillStyle = "#ffffff";
      ctx.fillText(badgeText, x1 + 8, badgeY + 15);
      ctx.font = "10px sans-serif";
      ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
      ctx.fillText(subText, x1 + 8, badgeY + 28);
    });
  }, [frameSummary]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
            <span>Live Classroom Face Verification</span>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                isWsConnected ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
              }`}
            >
              {isWsConnected ? "● Live Stream Active" : "○ Connecting WebSocket..."}
            </span>
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Real-time inference overlay with SCRFD bounding boxes, ArcFace cosine similarity, and temporal voting
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3 text-xs bg-gray-900/80 border border-gray-800 px-4 py-2 rounded-xl">
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
            <span className="text-emerald-400 font-semibold">Known (Green)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-rose-500 shadow-sm shadow-rose-500/50" />
            <span className="text-rose-400 font-semibold">Unknown (Red)</span>
          </div>
        </div>
      </div>

      {/* Main Stream + Track Inspector */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Live Video Canvas (3 Cols) */}
        <div className="xl:col-span-3 glass-card rounded-xl border border-gray-800 overflow-hidden relative bg-black aspect-video flex items-center justify-center">
          <img
            ref={imgRef}
            src={`${API_BASE_URL}/camera/stream`}
            alt="Real-time Stream"
            className="w-full h-full object-contain"
          />
          <canvas
            ref={canvasRef}
            className="absolute inset-0 pointer-events-none w-full h-full"
          />

          {/* Top Floating Telemetry Overlay */}
          <div className="absolute top-4 left-4 bg-black/80 backdrop-blur-md px-3.5 py-2 rounded-xl border border-white/10 text-xs flex items-center space-x-4">
            <div>
              <span className="text-gray-400">FPS: </span>
              <span className="font-mono font-bold text-white">
                {frameSummary?.fps ? frameSummary.fps.toFixed(1) : "30.0"}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Latency: </span>
              <span className="font-mono font-bold text-cyan-400">
                {frameSummary?.inference_latency_ms ? `${frameSummary.inference_latency_ms} ms` : "0 ms"}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Visible: </span>
              <span className="font-bold text-white">{frameSummary?.face_count ?? 0} faces</span>
            </div>
          </div>
        </div>

        {/* Live Active Tracks Sidebar (1 Col) */}
        <div className="glass-card rounded-xl border border-gray-800 p-4 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white pb-3 border-b border-gray-800">
              Active Detected Tracks ({frameSummary?.faces?.length ?? 0})
            </h3>

            <div className="mt-4 space-y-3 max-h-[500px] overflow-y-auto pr-1">
              {!frameSummary?.faces || frameSummary.faces.length === 0 ? (
                <div className="text-center py-12 text-gray-500 text-xs">
                  <span className="text-2xl block mb-2">🔍</span>
                  No faces detected in current frame.
                </div>
              ) : (
                frameSummary.faces.map((f) => (
                  <div
                    key={f.track_id}
                    onClick={() => setSelectedFace(f)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      f.status === "KNOWN"
                        ? "bg-emerald-950/25 border-emerald-700/50 hover:border-emerald-500"
                        : "bg-rose-950/25 border-rose-700/50 hover:border-rose-500"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">
                        {f.status === "KNOWN" ? f.name : "Unknown Face"}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                          f.status === "KNOWN"
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                        }`}
                      >
                        {f.status === "KNOWN" ? "KNOWN" : "UNKNOWN"}
                      </span>
                    </div>

                    <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-gray-400">
                      <div>
                        Similarity:{" "}
                        <span className="text-white font-mono">
                          {(f.similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        Quality:{" "}
                        <span className="text-white font-mono">
                          {(f.quality * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div>Track ID: #{f.track_id}</div>
                      <div>Liveness: {f.is_live ? "Verified" : "Bypass"}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-gray-800 text-[11px] text-gray-400">
            Temporal smoothing confirms identity over 8 sliding frames with 60% agreement.
          </div>
        </div>
      </div>
    </div>
  );
}
