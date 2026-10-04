import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Reconstruction() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function reconstruct() {
    setLoading(true);
    try {
      // In production, would call P2-01 backend
      // const res = await fetch("/api/reconstruct", { method: "POST" });
      // const data = await res.json();
      // setPrompt(data.prompt);
      setPrompt(
        "A cinematic shot of a character in an interior environment. " +
        "The subject performs a dramatic action with strong emotional undertones. " +
        "Camera uses a 35mm lens with shallow depth of field. Warm lighting " +
        "creates intimate shadows. Color palette teal and orange for cinematic " +
        "contrast. Composition follows rule of thirds. Audio includes ambient " +
        "room tone and subtle musical underscore."
      );
    } catch (err) {
      console.error("Reconstruction error:", err);
    } finally {
      setLoading(false);
    }
  }

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
                to="/app/storyboard"
                className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
              >
                Storyboard
              </li>
            <li>
              <a
                to="/app/quality"
                className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
              >
                Quality
              </li>
            </li>
            <li>
              <a
                to="/app/readiness"
                className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
              >
                Readiness
              </li>
            </li>
          </ul>
        </nav>
      </aside>

      <main className="ml-64 p-6 flex-1">
        <div className="max-w-2xl mx-auto">

          <div className="card p-8">
            <h2 className="font-bold text-2xl mb-6">Video-to-Video Reconstruction</h2>
            <p className="text-muted mb-8">
              Transform footage into optimized AI prompts using advanced analysis.
            </p>

            {/* Video preview area */}
            <div className="border rounded border-border h-64 bg-bg mb-8 flex items-center justify-center">
              <p className="text-muted">Video preview area</p>
            </div>

            {/* Generated prompt */}
            {prompt ? (
              <div>
                <h3 className="font-bold text-xl mb-4">Generated Production Prompt</h3>
                <p className="text-muted/2 mb-4">
                  {prompt}
                </p>
                <button
                  className="btn-primary w-full px-6 py-3 mb-4"
                  onClick={() => navigator.clipboard.writeText(prompt)}
                >
                  Copy Prompt
                </button>
                <button
                  className="btn-secondary w-full px-6 py-3 mb-4"
                >
                  Edit Prompt
                </button>
                <button
                  className="btn-secondary w-full px-6 py-3 mb-4"
                >
                  Regenerate
                </button>
              </div>
            ) : (
              <p className="text-muted mb-8">
                Upload and analyze a video to generate a production-ready prompt.
              </p>
            )}
          </div>
        </div>
      </main>
    </section>
  );
}