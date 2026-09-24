export interface FaceRecognitionResult {
  track_id: number;
  person_id: string | null;
  name: string;
  status: "KNOWN" | "UNKNOWN" | "LOW_QUALITY" | "VERIFYING";
  similarity: number;
  quality: number;
  bbox: [number, number, number, number];
  landmarks?: [number, number][];
  is_live: boolean;
  department?: string | null;
  class_name?: string | null;
  timestamp: string;
}

export interface RecognitionFrameSummary {
  frame_id: number;
  timestamp: string;
  camera_id: string;
  fps: number;
  face_count: number;
  known_count: number;
  unknown_count: number;
  inference_latency_ms: number;
  frame_width?: number;
  frame_height?: number;
  faces: FaceRecognitionResult[];
}

export interface Person {
  id: number;
  student_id: string;
  name: string;
  department?: string | null;
  class_name?: string | null;
  email?: string | null;
  profile_image?: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
  samples_count: number;
  samples?: {
    id: number;
    image_path: string;
    quality_score: number;
    created_at: string;
  }[];
}

export interface SystemInfo {
  platform: string;
  python_version: string;
  cpu_count_logical: number;
  cpu_count_physical: number;
  cpu_percent: number;
  ram_total_gb: number;
  ram_available_gb: number;
  ram_percent: number;
  active_models: {
    detector: string;
    recognizer: string;
  };
  vector_store_count: number;
  camera_status: {
    is_running: boolean;
    is_connected: boolean;
    current_fps: number;
    target_fps: number;
    resolution: string;
    total_frames: number;
    dropped_frames: number;
  };
}

export interface RecognitionEvent {
  id: number;
  person_id: number | null;
  student_id: string | null;
  name: string;
  track_id: number;
  status: string;
  similarity: number;
  quality: number;
  camera_id: string;
  bbox?: string | null;
  timestamp: string;
}
