import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [backendStatus, setBackendStatus] = useState("checking");

  // Check backend health
  async function checkBackend() {
    try {
      const res = await fetch("http://localhost:8000/api/health");
      const data = await res.json();
      setBackendStatus(data.status || "unavailable");
    } catch {
      setBackendStatus("unavailable");
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  }

  async function handleUpload() {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("http://localhost:8000/api/videos/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      console.log("Upload:", data);
      // Navigate to analysis workspace
      navigate("/app/analyze");
    } catch (err) {
      console.error("Upload error:", err);
    }
  }

  async function checkBackendHealth() {
    try {
      const res = await fetch("http://localhost:8000/api/health");
      const data = await res.json();
      return data.status || "unavailable";
    } catch {
      return "unavailable";
    }
  }

  // Initialize
  checkBackend();

  return (
    <section className="min-h-screen bg-bg text-fg">
      {/* Sidebar */}
      <aside className="fixed left-0 top-20 bottom-0 w-64 bg-bg-subtle border-r border-border flex flex-col">
        <div className="p-6 border-b border-border">
          <h2 className="font-bold text-xl tracking-tight text-accent">VisionPrompt AI</h2>
        </div>
        <nav className="flex-1">
          <ul className="space-y-2 p-4">
            <li>
              <a
                to="/app/analyze"
                className={({ location }) => location.pathname === "/app/analyze" || location.pathname === "/" ? "bg-accent text-fg" : "text-muted hover:text-accent transition-colors block px-4 py-2 rounded"}
              >
                Analyze Video
              </li>
              <li>
                <a
                  to="/app/reconstruction"
                  className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
                >
                  Reconstruction
                </li>
              <li>
                <a
                  to="/app/storyboard"
                  className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
                >
                  Storyboard
                </a>
              </li>
              <li>
                <a
                  to="/app/quality"
                  className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
                >
                  Quality
                </a>
              </li>
              <li>
                <a
                  to="/app/readiness"
                  className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
                >
                  Readiness
                </a>
              </li>
              <li>
                <a
                  to="/app/history"
                  className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
                >
                  History
                </a>
              </li>
              <li>
                <a
                  to="/app/batches"
                  className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
                >
                  Batches
                </a>
              </li>
              <li>
                <a
                  to="/app/projects"
                  className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
                >
                  Projects
                </a>
              </li>
            </ul>
          </nav>
        </aside>

        {/* Main content */}
        <main className="ml-64 p-6 flex-1">
          <div class="max-w-2xl mx-auto">
            {/* Welcome */}
            <div className="card p-8 mb-8">
              <h1 className="font-extrabold text-3xl mb-4">Turn your footage into production-ready prompts.</h1>
              <p className="text-muted">
                Upload a video to begin the AI-powered analysis pipeline.
              </p>
            </div>

            {/* Upload Card */}
            <div className="card p-8">
              <h2 className="font-bold text-2xl mb-6">Upload Video</h2>

              <p className="text-muted text-sm mb-6">
                Supported: MP4, MOV, MKV, WEBM, AVI • Max: 500MB
              </p>

              <input
                type="file"
                accept="video/mp4,video/mov,video/mkv,video/webm,video/avi"
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                onClick={() => document.querySelector('input[type="file"]')?.click()
                }
                className="btn-browse mb-4 inline-block"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                  <polygon points="13 2 3 14 12 14 11 2 13 2" />
                </svg>
                Browse Files
              </button>
              <button
                onClick={handleUpload}
                className="btn-analyze w-full mt-4 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!selectedFile}
              >
                {selectedFile ? "Start Analysis" : "Select a video first"}
              </button>

              {uploadProgress > 0 && (
                <div className="mt-4">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <span className="text-muted ml-2">
                    {uploadProgress}%
                  </span>
                </div>
              )}
            </div>

            {/* Recent Analyses */}
            <div className="card p-8">
              <h2 className="font-bold text-2xl mb-6">Recent Analyses</h2>
              <p className="text-muted">
                No analyses yet. Upload a video to get started.
              </p>
            </div>

            {/* System Status */}
            <div className="card p-8">
              <h2 className="font-bold text-2xl mb-6">System Status</h2>
              <div className="flex items-center gap-4">
                <span
                  className={backendStatus === "connected" ? "bg-accent text-bg" : "bg-card border border-border text-muted px-3 py-1 rounded"}
                >
                  {backendStatus}
                </span>
                <span className="text-muted">Backend API</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </section>
  );
}