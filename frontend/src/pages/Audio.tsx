import React from "react";

export default function AudioPanel() {
  return (
    <section className="min-h-screen bg-bg text-fg">
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
                <span className="absolute -right-1 rounded-full bg-red-500 text-white text-xs w-2 h-2"></span>
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
                to "/app/storyboard"
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
          </ul>
        </nav>
      </aside>

      <main className="ml-64 p-6 flex-1">
        <div className="max-w-7xl mx-auto">

          <div className="card p-6 mb-8">
            <h2 className="font-bold text-2xl mb-4">Audio</h2>
            <p className="text-muted">
              Audio analysis not available.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">

            <div>
              <h4 className="font-bold text-lg mb-4">Audio Detected</h4>
              <p className="text-muted">
                No audio detected
              </p>
              <p className="text-muted/2 text-sm">
                Heuristic: no significant audio track found.
              </p>
            </div>

            <div>
              <h4 className="font-bold text-lg mb-4">Transcript</h4>
              <p className="text-muted">
                Transcription unavailable.
              </p>
              <p className="text-muted/2 text-sm">
                No transcription model configured.
              </p>
            </div>

            <div>
              <h4 className="font-bold text-lg mb-4">Speech Segments</h4>
              <p className="text-muted">
                No speech segments.
              </p>
              <p className="text-muted/2 text-sm">
                Audio not available for segmentation.
              </p>
            </div>

          </div>

          <div className="mt-8">
            <p className="text-muted/2">
              Provider status: MOCK/UNAVAILABLE. No AI speech recognition model
              configured. Audio analysis pipeline reports no audio data suitable
              for transcription.
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}