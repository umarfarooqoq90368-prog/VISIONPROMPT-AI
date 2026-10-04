import React from "react";

export default function Readiness() {
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
                to "/app/quality"
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
            <h2 className="font-bold text-2xl mb-4">Production Readiness</h2>
            <p className="text-muted">
              Readiness assessment for production deployment.
            </p>
          </div>

          {/* Large readiness score */}
          <div className="text-center mb-8">
            <div className="status-badge-large pass">
              82%
            </div>
            <p className="text-muted mt-2">Overall Readiness</p>
          </div>

          {/* Categories */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            
            <div>
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-2">75%</div>
                <div className="text-muted">Visual</div>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: "75%" }} />
              </div>
            </div>

            <div>
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-2">65%</div>
                <div className="text-muted">Camera</div>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: "65%" }} />
              </div>
            </div>

            <div>
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-2">90%</div>
                <div className="text-muted">Character</div>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: "90%" }} />
              </div>
            </div>

            <div>
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-2">70%</div>
                <div className="text-muted">Action</div>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: "70%" }} />
              </div>
            </div>

            <div>
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-2">85%</div>
                <div className="text-muted">Environment</div>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: "85%" }} />
              </div>
            </div>

            <div>
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-2">80%</div>
                <div className="text-muted">Color</div>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: "80%" }} />
              </div>
            </div>

          </div>

          {/* Status legend */}
          <div className="mt-8 p-4 bg-card border border-border rounded">
            <p className="text-sm text-muted">
              <span className="text-green-400 mr-2">PASS</span>
              <span className="text-warning mr-2">WARNING</span>
              <span className="text-red-400">FAIL</span>
              <span className="text-muted">UNAVAILABLE</span>
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}