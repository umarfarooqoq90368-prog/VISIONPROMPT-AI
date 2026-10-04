import React from "react";

export default function Quality() {
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
                to "/app/readiness"
                className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
              >
                Readiness
              </a>
            </li>
          </ul>
        </nav>
      </aside>

      <main className="ml-64 p-6 flex-1">
        <div className="max-w-7xl mx-auto">

          <div className="card p-6 mb-8">
            <h2 className="font-bold text-2xl mb-4">Prompt Quality</h2>
            <p className="text-muted">
              Quality analysis using backend metrics.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">

            {/* Overall Quality */}
            <div>
              <h3 className="font-bold text-lg mb-3">Overall Quality Score</h3>
              <div className="text-3xl font-bold text-accent">78%</div>
              <p className="text-muted text-sm">
                Of 100 possible points
              </p>
            </div>

            {/* Completeness */}
            <div>
              <h3 className="font-bold text-lg mb-3">Completeness</h3>
              <div className="text-3xl font-bold mb-2">65%</div>
              <p className="progress-bar">
                <div className="progress-fill" style={{ width: "65%" }} />
              </div>
              <p className="text-muted text-xs">All required prompt sections present</p>
            </div>

            {/* Specificity */}
            <div>
              <h3 className="font-bold text-lg mb-3">Specificity</h3>
              <div className="text-3xl font-bold mb-2">55%</div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: "55%" }} />
              </div>
              <p className="text-muted text-xs">Prompt includes concrete details</p>
            </div>

          </div>

          {/* Recommendations */}
          <div className="card p-6 mt-8">
            <h3 className="font-bold text-lg mb-3">Recommendations</h3>
            <ul className="text-muted text-sm">
              <li>Add more specific character descriptions</li>
              <li>Include lighting conditions for each scene</li>
              <li>Specify camera lens and focal length</li>
              <li>Add continuity notes between shots</li>
            </ul>
          </div>
        </div>
      </main>
    </section>
  );
}