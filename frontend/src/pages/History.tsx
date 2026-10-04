import React from "react";

export default function History() {
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
            <h2 className="font-bold text-2xl mb-4">History & Versions</h2>
            <p className="text-muted">
              Previous analyses and prompts.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">

            {/* Recent Analysis */}
            <div>
              <h3 className="font-bold text-lg mb-4">Recent Analyses</h3>
              <ul className="space-y-3 text-muted">
                <li>No analyses yet. Upload a video to begin.</li>
                <li>Analysis #1: Shot detection + prompt generation</li>
                <li>Analysis #2: Camera estimation + color palette</li>
              </ul>
            </div>

            {/* Prompt Versions */}
            <div>
              <h3 className="font-bold text-lg mb-4">Prompt Versions</h3>
              <ul className="space-y-3 text-muted">
                <li>No versions yet. Generate a prompt to create versions.</li>
                <li>Version 1.0: Initial prompt generation</li>
                <li>Version 1.1: Refined prompt with continuity notes</li>
              </ul>
            </div>

            {/* Favorites */}
            <div>
              <h3 className="font-bold text-lg mb-4">Favorites</h3>
              <ul className="space-y-3 text-muted">
                <li>No favorites yet. Star prompts to save them.</li>
                <li>Tag: cinematic</li>
                <li>Tag: dramatic</li>
              </ul>
            </div>

          </div>

          {/* Actions */}
          <div className="card p-6 mt-8">
            <h3 className="font-bold text-lg mb-3">Actions</h3>
            <p className="text-muted">
              Open, Compare, Export, Delete supported analyses.
            </p>
            <p className="text-muted/2 text-xs">
              Use the sidebar navigation to access previous work.
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}