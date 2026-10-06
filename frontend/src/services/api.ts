export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const endpoints = {
  upload: "/api/videos/upload",
  health: "/api/health",

  shots: (filename: string) => `/api/videos/${filename}/shots/detect`,
  camera: (filename: string) => `/api/videos/${filename}/camera/estimate`,
  color: (filename: string) => `/api/videos/${filename}/color/analyze`,
  emotion: (filename: string) => `/api/videos/${filename}/emotion-action/analyze`,
  characters: (filename: string) => `/api/videos/${filename}/characters/consistency`,
  batch: "/api/batches",
  reference: (filename: string) => `/api/videos/${filename}/reference/analyze`,
  storyboard: (filename: string) => `/api/videos/${filename}/storyboard`,
  register: "/api/v1/auth/register",
  login: "/api/v1/auth/login",
  projects: "/api/v1/projects",
  batches: "/api/v1/batches",
};