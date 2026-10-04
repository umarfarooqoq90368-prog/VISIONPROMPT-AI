import React, { useState, useEffect } from "react";

export default function AnalysisWorkspace() {
  const [stages, setStages] = useState<Record<string, string>>({
    Upload: "complete",
    "Metadata": "complete",
    "Frame Extraction": "complete",
    "Shot Detection": "processing",
    "Visual Intelligence": "pending",
    "Camera/Lens": "pending",
    Color: "pending",
    "Emotion/Action": "pending",
    "Character Consistency": "pending",
    Audio: "pending",
    Reconstruction: "pending",
    Storyboard: "pending",
    Quality: "pending",
    Readiness: "pending",
  });
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);

  // Initialize stages from backend if available
  useEffect(() => {
    // In production, would fetch from backend
    // const stagesFromBackend = fetchStagesFromBackend();
    // setStages(stagesFromBackend);
  }, []);

  const stageOrder = [
    "Upload",
    "Metadata",
    "Frame Extraction",
    "Shot Detection",
    "Visual Intelligence",
    "Camera/Lens",
    "Color",
    "Emotion/Action",
    "Character Consistency",
    "Audio",
    "Reconstruction",
    "Storyboard",
    "Quality",
    "Readiness",
  ];

  const statusClass = (status: string) => {
    switch (status) {
      case "complete": return "bg-green-500/20 text-green-400";
      case "processing": return "bg-yellow-500/20 text-yellow-400";
      case "pending": return "bg-blue-500/20 text-blue-400";
      case "failed": return "bg-red-500/20 text-red-400";
      case "unavailable": return "bg-gray-500/20 text-gray-400";
      default: return "bg-gray-500/20 text-gray-400";
    }
  };

  const statusText = (status: string) => {
    switch (status) {
      case "complete": return "Complete";
      case "processing": return "Processing";
      case "pending": return "Pending";
      case "failed": return "Failed";
      case "unavailable": return "Unavailable";
      default: return "Unknown";
    }
  };

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
                className="relative pr-4"
              >
                <span className="absolute -right-1 rounded-full bg-red-500 text-white text-xs w-2 h-2" style={{ animation: 'blink 1s infinite' }}></span>
                Analyze Video
              </a>
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
        <div class="max-w-7xl mx-auto">

          {/* Video info card */}
          <div className="card p-6 mb-8">
            <h2 className="font-bold text-2xl mb-4">Video Analysis Workspace</h2>
            <p className="text-muted">
              Select a video from the upload page or access recent analyses.
            </p>
          </div>

          {/* Processing Pipeline */}
          <div className="card p-6 mb-8">
            <h2 className="font-bold text-2xl mb-6">Processing Pipeline</h2>
            <ul className="space-y-2">
              {stageOrder.map((stage, index) => {
                const status = stages[stage] || "unavailable";
                return (
                  <li key={stage} className="flex items-center gap-3">
                    <span className="flex-shrink-0">
                      {index + 1}.
                    </span>
                    <span className="text-muted truncate w-48">{stage}</span>
                    <span
                      className={`stage-badge ${statusClass(status)}`}
                    >
                      {statusText(status)}
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>

          {/* Analysis Panels layout - 3 column on desktop, 1 column on mobile */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            
            {/* Left: Video Player */}
            <div className="col-span-1 md:col-span-1">
              <div className="card p-6">
                <h3 className="font-bold text-xl mb-4">Video Player</h3>
                <p className="text-muted text-sm">
                  Video preview will appear here. Supports MP4, MOV, MKV, WEBM, AVI.
                </p>
                <div className="border rounded border-border h-64 bg-bg mt-4 flex items-center justify-center">
                  <p className="text-muted">Upload a video to preview</p>
                </div>
              </div>
            </div>

            {/* Center: Timeline / Stages */}
            <div className="col-span-1 md:col-span-2">
              <div className="card p-6">
                <h3 className="font-bold text-xl mb-4">Processing Timeline</h3>
                <p className="text-muted text-sm">
                  Track the progress of each analysis stage.
                </p>
                {/* Pipeline already rendered above */}
              </div>
            </div>

            {/* Right: Analysis Panels */}
            <div className="col-span-1 md:col-span-2">
              <div className="space-y-4">
                
                {/* Shot Detection Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Shot Detection</h4>
                  <p className="text-muted">
                    Using P2-02 heuristic shot boundary detection.
                  </p>
                  <p className="text-muted/2 text-sm mb-2">
                    Provider: Heuristic
                  </p>
                  <p className="text-muted/2 text-xs">
                    Camera estimation unavailable - using heuristic method.
                  </p>
                </div>

                {/* Camera & Lens Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Camera & Lens</h4>
                  <p className="text-muted">
                    Using P2-03 estimation.
                  </p>
                  <p className="text-muted/2 text-sm mb-2">
                    Focal length estimation unavailable.
                  </p>
                  <p className="text-muted/2 text-xs">
                    Lens category: unavailable.
                  </p>
                </div>

                {/* Color Intelligence Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Color Intelligence</h4>
                  <p className="text-muted">
                    Using P2-04 color analysis.
                  </p>
                  <p className="text-muted/2 text-sm mb-2">
                    Dominant colors will appear here.
                  </p>
                </div>

                {/* Emotion & Action Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Emotion & Action</h4>
                  <p className="text-muted">
                    Using P2-05 analysis.
                  </p>
                  <p className="text-muted/2 text-sm mb-2">
                    Observed actions: none detected.
                  </p>
                  <p className="text-muted/2 text-xs">
                    Inferred emotion: unavailable.
                  </p>
                  <p className="text-muted/2 text-xs small">
                    Never present inferred emotion as confirmed fact.
                  </p>
                </div>

                {/* Character Consistency Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Character Consistency</h4>
                  <p className="text-muted">
                    Using P2-06 subject tracking.
                  </p>
                  <p className="text-muted/2 text-sm mb-2">
                    No characters detected.
                  </p>
                  <p className="text-muted/2 text-xs">
                    Subject tracking without biometric identification.
                  </p>
                </div>

                {/* Audio Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Audio</h4>
                  <p className="text-muted">
                    Audio transcription not available.
                  </p>
                  <p className="text-muted/2 text-sm">
                    Provider: mock / unavailable.
                  </p>
                </div>

                {/* Reconstruction Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Reconstruction</h4>
                  <p className="text-muted">
                    P2-01 video-to-prompt reconstruction.
                  </p>
                  <p className="text-muted/2 text-sm mb-2">
                    Ready to generate prompt when analysis complete.
                  </p>
                </div>

                {/* Quality Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Quality</h4>
                  <p className="text-muted">
                    Quality analysis pending.
                  </p>
                </div>

                {/* Readiness Panel */}
                <div>
                  <h4 className="font-bold text-lg mb-4">Readiness</h4>
                  <p className="text-muted">
                    Ready for production.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </section>
  );
}