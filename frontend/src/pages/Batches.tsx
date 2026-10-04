import React from "react";

export default function Batches() {
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
            <h2 className="font-bold text-2xl mb-4">Batch Processing</h2>
            <p className="text-muted">
              Process multiple videos simultaneously.
            </p>
          </div>

          {/* Create batch section */}
          <div className="card p-6 mb-8">
            <h3 className="font-bold text-lg mb-3">Create New Batch</h3>
            <p className="text-muted mb-4">
              Select multiple videos to process together.
            </p>
            <button
              className="btn-primary w-full px-6 py-3 mb-4"
            >
              Create New Batch
            </button>
          </div>

          {/* Batch list */}
          <div>
            <h3 className="font-bold text-lg mb-3">Active Batches</h3>
            <p className="text-muted">
              No active batches. Create a new batch to get started.
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}