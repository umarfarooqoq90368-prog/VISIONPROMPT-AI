import React from "react";

export default function EmotionAction() {
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
            <h2 className="font-bold text-2xl mb-4">Emotion & Action Analysis</h2>
            <p className="text-muted">
              Using P2-05 emotion and action detection.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">

            {/* Observed Actions */}
            <div>
              <h4 className="font-bold text-lg mb-4">Observed Actions</h4>
              <p className="text-muted">
                No observed actions detected.
              </p>
              <p className="text-muted/2 text-xs">
                Heuristic analysis: no significant motion patterns identified.
              </p>
            </div>

            {/* Inferred Actions */}
            <div>
              <h4 className="font-bold text-lg mb-4">Inferred Actions</h4>
              <p className="text-muted">
                Inference unavailable.
              </p>
              <p className="text-muted/2 text-xs">
                Never present inferred action as confirmed fact.
              </p>
            </div>

            {/* Inferred Emotions */}
            <div>
              <h4 className="font-bold text-lg mb-4">Inferred Emotions</h4>
              <p className="text-muted">
                Emotion inference unavailable.
              </p>
              <p className="text-muted/2 text-xs">
                Important: Inferred emotion is NOT a confirmed fact. Labels such as
                "Observed" and "Inferred" clearly distinguish confidence levels.
              </p>
            </div>

          </div>

          <div className="mt-8">
            <p className="text-muted/2">
              Provider status: HEURISTIC. Action/emotion detection using heuristic
              methods only. No AI model inference claimed. Confidence scores not
              available without real model.
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}