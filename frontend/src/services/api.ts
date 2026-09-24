import { Person, SystemInfo, RecognitionEvent } from "../types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

export async function fetchHealth(): Promise<{ status: string; uptime_seconds: number }> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error("Failed to fetch health status");
  return res.json();
}

export async function fetchSystemInfo(): Promise<SystemInfo> {
  const res = await fetch(`${API_BASE_URL}/system/info`);
  if (!res.ok) throw new Error("Failed to fetch system info");
  return res.json();
}

export async function fetchPersons(search?: string): Promise<Person[]> {
  const url = search ? `${API_BASE_URL}/persons?search=${encodeURIComponent(search)}` : `${API_BASE_URL}/persons`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch registered persons");
  return res.json();
}

export async function createPerson(data: {
  student_id: string;
  name: string;
  department?: string;
  class_name?: string;
  email?: string;
}): Promise<Person> {
  const res = await fetch(`${API_BASE_URL}/persons`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create person");
  }
  return res.json();
}

export async function deletePerson(id: number): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE_URL}/persons/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete person");
  return res.json();
}

export async function enrollSamples(
  personId: number,
  samples: { image_base64: string; quality_score: number }[]
): Promise<{
  student_id: string;
  name: string;
  total_submitted: number;
  accepted: number;
  rejected: number;
  rejection_reasons: string[];
  total_registered_embeddings: number;
}> {
  const res = await fetch(`${API_BASE_URL}/persons/${personId}/enroll`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ samples }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to enroll samples");
  }
  return res.json();
}

export async function fetchEvents(limit: number = 50): Promise<RecognitionEvent[]> {
  const res = await fetch(`${API_BASE_URL}/events?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function toggleCamera(start: boolean): Promise<any> {
  const endpoint = start ? "/camera/start" : "/camera/stop";
  const res = await fetch(`${API_BASE_URL}${endpoint}`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to control camera");
  return res.json();
}

export async function togglePipeline(start: boolean): Promise<any> {
  const endpoint = start ? "/recognition/start" : "/recognition/stop";
  const res = await fetch(`${API_BASE_URL}${endpoint}`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to control recognition pipeline");
  return res.json();
}
