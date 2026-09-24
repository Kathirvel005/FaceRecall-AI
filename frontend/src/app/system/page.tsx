"use client";

import { useEffect, useState } from "react";
import { fetchSystemInfo } from "../../services/api";
import { SystemInfo } from "../../types";

export default function SystemPage() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchSystemInfo()
      .then(setSystemInfo)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-gray-800">
        <h2 className="text-2xl font-bold tracking-tight text-white">System Diagnostics & Architecture</h2>
        <p className="text-sm text-gray-400">
          Hardware telemetry, neural model paths, execution providers, and threshold calibration
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-gray-400">Loading hardware diagnostics...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Hardware Telemetry */}
          <div className="glass-card p-6 rounded-xl border border-gray-800 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
              <span>💻</span>
              <span>Host Hardware Telemetry</span>
            </h3>

            <div className="space-y-2 text-xs divide-y divide-gray-800/80">
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Platform & OS</span>
                <span className="text-white font-mono">{systemInfo?.platform}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Python Version</span>
                <span className="text-white font-mono">{systemInfo?.python_version}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">CPU Architecture</span>
                <span className="text-white font-mono">
                  {systemInfo?.cpu_count_physical} Cores / {systemInfo?.cpu_count_logical} Threads
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">CPU Utilization</span>
                <span className="text-cyan-400 font-mono font-bold">
                  {systemInfo?.cpu_percent ?? 0}%
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Physical RAM</span>
                <span className="text-white font-mono">
                  {systemInfo?.ram_available_gb} GB free / {systemInfo?.ram_total_gb} GB total ({systemInfo?.ram_percent}%)
                </span>
              </div>
            </div>
          </div>

          {/* Card 2: Neural Models & Inference */}
          <div className="glass-card p-6 rounded-xl border border-gray-800 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
              <span>🧠</span>
              <span>Deep Learning Inference Engines</span>
            </h3>

            <div className="space-y-2 text-xs divide-y divide-gray-800/80">
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Face Detector</span>
                <span className="text-emerald-400 font-mono">SCRFD ResNet-10G ONNX</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Face Recognizer</span>
                <span className="text-emerald-400 font-mono">ArcFace ResNet50 (512-D)</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Detector Weights</span>
                <span className="text-white font-mono text-[11px]">
                  {systemInfo?.active_models?.detector}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Recognizer Weights</span>
                <span className="text-white font-mono text-[11px]">
                  {systemInfo?.active_models?.recognizer}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">FAISS Index Entries</span>
                <span className="text-cyan-400 font-mono font-bold">
                  {systemInfo?.vector_store_count ?? 0} vectors
                </span>
              </div>
            </div>
          </div>

          {/* Card 3: Calibrated Quality & Recognition Thresholds */}
          <div className="glass-card p-6 rounded-xl border border-gray-800 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
              <span>🎯</span>
              <span>Calibrated Decision Thresholds</span>
            </h3>

            <div className="space-y-2 text-xs divide-y divide-gray-800/80">
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Similarity Threshold (Known)</span>
                <span className="text-emerald-400 font-mono font-bold">≥ 0.50 (Cosine Similarity)</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Unknown Threshold</span>
                <span className="text-rose-400 font-mono font-bold">&lt; 0.40 (Explicit Unknown)</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Minimum Face Size</span>
                <span className="text-white font-mono">60 x 60 px</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Motion Blur Limit</span>
                <span className="text-white font-mono">Laplacian Variance ≥ 50.0</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Temporal Smoothing</span>
                <span className="text-white font-mono">8-Frame Window · 60% Ratio</span>
              </div>
            </div>
          </div>

          {/* Card 4: Camera Subsystem Status */}
          <div className="glass-card p-6 rounded-xl border border-gray-800 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
              <span>📹</span>
              <span>Camera Subsystem Status</span>
            </h3>

            <div className="space-y-2 text-xs divide-y divide-gray-800/80">
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Capture Thread</span>
                <span
                  className={`font-mono font-bold ${
                    systemInfo?.camera_status?.is_running ? "text-emerald-400" : "text-gray-500"
                  }`}
                >
                  {systemInfo?.camera_status?.is_running ? "RUNNING" : "STOPPED"}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Resolution</span>
                <span className="text-white font-mono">
                  {systemInfo?.camera_status?.resolution ?? "1280x720"}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Frame Dropping Mechanism</span>
                <span className="text-emerald-400 font-mono">Active (Zero-Lag Atomic Buffer)</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-400">Dropped Frames (Slow Consumer)</span>
                <span className="text-gray-400 font-mono">
                  {systemInfo?.camera_status?.dropped_frames ?? 0}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
