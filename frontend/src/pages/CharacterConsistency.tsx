import React from "react";

export default function CharacterConsistency() {
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
            <h2 className="font-bold text-2xl mb-4">Character Consistency</h2>
            <p className="text-muted">
              Using P2-06 subject tracking heuristic.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">

            {/* Character Tracking */}
            <div>
              <h4 className="font-bold text-lg mb-4">Subject Tracking</h4>
              <p className="text-muted">
                No characters detected in current analysis.
              </p>
              <p className="text-muted/2 text-xs">
                Subject tracking performed via heuristic frame differencing.
                No biometric identification or real-person recognition performed.
              </p>
            </div>

            {/* Consistency Stats */}
            <div>
              <h4 className="font-bold text-lg mb-4">Consistency Metrics</h4>
              <p className="text-muted mb-2">
                Consistency score: N/A
              </p>
              <p className="text-muted text-sm">
                Appearance count: 0
              </p>
              <p className="text-muted text-xs">
                Frames analyzed: 0
              </p>
              <p className="text-muted text-xs">
                Changed attributes: N/A
              </p>
            </div>

          </div>

          <div className="mt-8">
            <p className="text-muted/2">
              Provider status: HEURISTIC. Character consistency using subject
              tracking heuristic from P2-06. No biometric identification, no
              real-person identification performed. Results are heuristic estimates
              only.
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}