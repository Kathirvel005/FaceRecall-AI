"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL, createPerson, enrollSamples } from "../../../services/api";

export default function RegisterStudentPage() {
  const router = useRouter();

  // Step state: 1 = Form, 2 = Camera Capture, 3 = Confirm/Submitting
  const [step, setStep] = useState<number>(1);

  // Form State
  const [studentId, setStudentId] = useState("");
  const [name, setName] = useState("");
  const [department, setDepartment] = useState("");
  const [className, setClassName] = useState("");
  const [email, setEmail] = useState("");

  // Camera & Samples State
  const [useServerCam, setUseServerCam] = useState<boolean>(true);
  const [capturedSamples, setCapturedSamples] = useState<string[]>([]);
  const [isCapturingAuto, setIsCapturingAuto] = useState<boolean>(false);
  const [streamActive, setStreamActive] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [enrollmentResult, setEnrollmentResult] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Start browser webcam only if not using server cam and on step 2
  useEffect(() => {
    if (step === 2 && !useServerCam) {
      startBrowserCamera();
    } else {
      stopBrowserCamera();
    }
    return () => stopBrowserCamera();
  }, [step, useServerCam]);

  const startBrowserCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setStreamActive(true);
    } catch (err) {
      console.error("Camera access error:", err);
      setErrorMessage("Could not access browser camera. Switching to Server Stream mode.");
      setUseServerCam(true);
    }
  };

  const stopBrowserCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setStreamActive(false);
  };

  const captureSingleSample = async () => {
    setErrorMessage(null);
    if (useServerCam) {
      try {
        const res = await fetch(`${API_BASE_URL}/camera/snapshot`);
        if (!res.ok) throw new Error("Could not grab server camera snapshot");
        const blob = await res.blob();
        const reader = new FileReader();
        reader.onloadend = () => {
          if (reader.result) {
            setCapturedSamples((prev) => [...prev, reader.result as string]);
          }
        };
        reader.readAsDataURL(blob);
      } catch (err: any) {
        setErrorMessage("Snapshot capture error: " + err.message);
      }
    } else {
      if (!videoRef.current) return;
      const canvas = document.createElement("canvas");
      canvas.width = videoRef.current.videoWidth || 640;
      canvas.height = videoRef.current.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      const base64 = canvas.toDataURL("image/jpeg", 0.90);
      setCapturedSamples((prev) => [...prev, base64]);
    }
  };

  const startAutoCapture = () => {
    setIsCapturingAuto(true);
    let count = 0;
    const target = 15;
    const interval = setInterval(async () => {
      await captureSingleSample();
      count++;
      if (count >= target) {
        clearInterval(interval);
        setIsCapturingAuto(false);
      }
    }, 400);
  };

  const removeSample = (index: number) => {
    setCapturedSamples((prev) => prev.filter((_, i) => i !== index));
  };

  const handleFinalSubmit = async () => {
    if (capturedSamples.length === 0) {
      alert("Please capture at least 5-10 face samples before enrolling.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      // 1. Create Person in Database
      const newPerson = await createPerson({
        student_id: studentId.trim(),
        name: name.trim(),
        department: department.trim() || undefined,
        class_name: className.trim() || undefined,
        email: email.trim() || undefined,
      });

      // 2. Submit Samples for Quality Check, ArcFace Embedding, and FAISS indexing
      const samplesPayload = capturedSamples.map((s) => ({
        image_base64: s,
        quality_score: 1.0,
      }));

      const res = await enrollSamples(newPerson.id, samplesPayload);
      setEnrollmentResult(res);
      setStep(3);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to complete enrollment.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Student Biometric Enrollment</h2>
          <p className="text-sm text-gray-400">
            Multi-sample capture, landmark alignment, and FAISS vector indexing
          </p>
        </div>
        <Link href="/persons" className="text-xs text-cyan-400 hover:underline">
          Back to Registry
        </Link>
      </div>

      {/* Step Indicators */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#0e1424] rounded-xl border border-gray-800 text-xs font-medium">
        <span className={step >= 1 ? "text-cyan-400" : "text-gray-500"}>
          1. Student Information
        </span>
        <span className="text-gray-600">→</span>
        <span className={step >= 2 ? "text-cyan-400" : "text-gray-500"}>
          2. Multi-Sample Capture ({capturedSamples.length}/15)
        </span>
        <span className="text-gray-600">→</span>
        <span className={step >= 3 ? "text-emerald-400" : "text-gray-500"}>
          3. Indexing & Confirmation
        </span>
      </div>

      {errorMessage && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs rounded-lg">
          {errorMessage}
        </div>
      )}

      {/* STEP 1: METADATA FORM */}
      {step === 1 && (
        <div className="glass-card p-6 rounded-xl border border-gray-800 space-y-4">
          <h3 className="text-sm font-semibold text-white">Enter Student Details</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Student ID *
              </label>
              <input
                type="text"
                required
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                placeholder="e.g. STU001 or 2026CS101"
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Kathirvel S"
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Department
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Computer Science & AI"
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Class / Section
              </label>
              <input
                type="text"
                value={className}
                onChange={(e) => setClassName(e.target.value)}
                placeholder="e.g. Final Year CSE-A"
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Email Address (Optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. student@college.edu"
                className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              onClick={() => {
                if (!studentId || !name) {
                  alert("Student ID and Full Name are required.");
                  return;
                }
                setStep(2);
              }}
              className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white rounded-lg text-sm font-medium shadow-md shadow-cyan-900/20 transition"
            >
              Continue to Camera Capture →
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: CAMERA CAPTURE */}
      {step === 2 && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Live Camera View (2 Cols) */}
            <div className="lg:col-span-2 glass-card rounded-xl border border-gray-800 overflow-hidden flex flex-col">
              <div className="p-3 border-b border-gray-800/80 bg-[#0e1424] flex items-center justify-between text-xs">
                <span className="font-semibold text-white">Enrollment Camera Feed</span>
                <div className="flex items-center space-x-2">
                  <span className="text-gray-400">Source:</span>
                  <button
                    onClick={() => setUseServerCam(!useServerCam)}
                    className="px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 text-cyan-400 font-mono text-[11px] border border-gray-700"
                  >
                    {useServerCam ? "System Camera" : "Browser Webcam"}
                  </button>
                </div>
              </div>

              <div className="relative bg-black aspect-video flex items-center justify-center">
                {useServerCam ? (
                  <img
                    src={`${API_BASE_URL}/camera/stream`}
                    alt="System Camera Stream"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-contain"
                  />
                )}
                {/* Oval Guide Overlay */}
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                  <div className="w-48 h-64 border-2 border-dashed border-cyan-400/60 rounded-full" />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="p-4 bg-[#0e1424] border-t border-gray-800 flex items-center justify-between gap-3">
                <button
                  onClick={captureSingleSample}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-xs font-medium transition"
                >
                  📸 Capture Single Sample
                </button>
                <button
                  onClick={startAutoCapture}
                  disabled={isCapturingAuto}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-medium transition shadow-md shadow-cyan-900/20"
                >
                  {isCapturingAuto ? "Capturing 15 Variations..." : "⚡ Auto-Capture 15 Samples"}
                </button>
              </div>
            </div>

            {/* Quality Guidance & Progress (1 Col) */}
            <div className="glass-card p-4 rounded-xl border border-gray-800 flex flex-col justify-between">
              <div>
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-2">
                  Enrollment Guidance
                </h4>
                <ul className="text-xs text-gray-400 space-y-2">
                  <li>✔ Capture 10 to 20 face samples</li>
                  <li>✔ Vary expressions slightly (neutral, smile)</li>
                  <li>✔ Slight head rotations (left, right, up, down)</li>
                  <li>✔ Ensure classroom lighting is active</li>
                  <li>✖ Avoid blurred or partially covered faces</li>
                </ul>

                <div className="mt-6">
                  <div className="flex items-center justify-between text-xs font-medium mb-1">
                    <span className="text-gray-300">Samples Captured</span>
                    <span className="text-cyan-400 font-mono font-bold">
                      {capturedSamples.length} / 15
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-cyan-500 to-emerald-500 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(100, (capturedSamples.length / 15) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2 pt-4 border-t border-gray-800">
                <button
                  onClick={handleFinalSubmit}
                  disabled={capturedSamples.length < 5 || isSubmitting}
                  className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition shadow-md shadow-emerald-900/20"
                >
                  {isSubmitting ? "Generating Embeddings..." : "✔ Finalize & Register Student"}
                </button>
                <button
                  onClick={() => setStep(1)}
                  className="w-full py-2 bg-gray-800/80 hover:bg-gray-800 text-gray-300 rounded-lg text-xs transition"
                >
                  ← Back to Details
                </button>
              </div>
            </div>
          </div>

          {/* Captured Sample Thumbnails Gallery */}
          {capturedSamples.length > 0 && (
            <div className="glass-card p-4 rounded-xl border border-gray-800">
              <h4 className="text-xs font-semibold text-white mb-3">
                Captured Samples ({capturedSamples.length})
              </h4>
              <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
                {capturedSamples.map((imgSrc, i) => (
                  <div key={i} className="relative group rounded-lg overflow-hidden border border-gray-800 aspect-square">
                    <img src={imgSrc} alt={`Sample ${i}`} className="w-full h-full object-cover" />
                    <button
                      onClick={() => removeSample(i)}
                      className="absolute top-1 right-1 w-5 h-5 bg-rose-600/90 hover:bg-rose-600 text-white rounded-full flex items-center justify-center text-[10px] opacity-0 group-hover:opacity-100 transition"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 3: CONFIRMATION */}
      {step === 3 && enrollmentResult && (
        <div className="glass-card p-8 rounded-xl border border-emerald-500/40 text-center space-y-4 max-w-lg mx-auto">
          <div className="w-16 h-16 bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center text-3xl mx-auto text-emerald-400">
            ✓
          </div>
          <h3 className="text-xl font-bold text-white">Enrollment Successfully Completed!</h3>
          <p className="text-xs text-gray-300">
            Student <span className="font-bold text-white">{enrollmentResult.name}</span> (ID: {enrollmentResult.student_id}) has been registered and indexed in the FAISS vector database.
          </p>

          <div className="bg-[#0e1424] p-4 rounded-lg border border-gray-800 text-xs grid grid-cols-2 gap-2 text-left">
            <div>Accepted Embeddings: <span className="text-emerald-400 font-bold">{enrollmentResult.accepted}</span></div>
            <div>Rejected Samples: <span className="text-rose-400 font-bold">{enrollmentResult.rejected}</span></div>
            <div className="col-span-2 pt-1 border-t border-gray-800 text-gray-400">
              Total Vector Database Size: <span className="text-cyan-400 font-bold">{enrollmentResult.total_registered_embeddings} identities</span>
            </div>
          </div>

          <div className="pt-4 flex justify-center space-x-3">
            <Link
              href="/recognition"
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-emerald-600 text-white text-xs font-medium rounded-lg shadow-md transition"
            >
              Test in Live Recognition →
            </Link>
            <button
              onClick={() => {
                setStudentId("");
                setName("");
                setDepartment("");
                setClassName("");
                setEmail("");
                setCapturedSamples([]);
                setEnrollmentResult(null);
                setStep(1);
              }}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium rounded-lg transition"
            >
              Enroll Another Student
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
