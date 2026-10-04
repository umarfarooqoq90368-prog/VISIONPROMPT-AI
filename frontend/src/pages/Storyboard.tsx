import React from "react";

export default function Storyboard() {
  // Sample storyboard data from P2-09
  const shots = [
    {
      id: 1,
      timestamp: 0.0,
      duration: 8.5,
      transition: "cut",
      scene: "Exterior - Day",
      subject: "Protagonist",
      action: "Walking toward camera",
      environment: "Street",
      camera: "Static, 35mm lens",
      lens: "35mm",
      lighting: "Natural daylight",
      color: "#00d4aa, #1a1a24",
      composition: "Rule of thirds",
      audio: "Ambient street sound",
      continuity: "Match cut to next scene",
    },
    {
      id: 2,
      timestamp: 8.5,
      duration: 6.0,
      transition: "fade",
      scene: "Interior - Kitchen",
      subject: "Protagonist",
      action: "Preparing food",
      environment: "Kitchen",
      camera: "Handheld, 50mm lens",
      lens: "50mm",
      lighting: "Warm practical lights",
      color: "#ff8c42, #2d3748",
      composition: "Centered",
      audio: "Frying sounds",
      continuity: " continuity with previous",
    },
  ];

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
                to "/app/quality"
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
          </ul>
        </nav>
      </aside>

      <main className="ml-64 p-6 flex-1">
        <div className="max-w-7xl mx-auto">

          <div className="card p-6 mb-8">
            <h2 className="font-bold text-2xl mb-4">AI Storyboard</h2>
            <p className="text-muted">
              Generated from P2-09 analysis.
            </p>
          </div>

          <div className="space-y-4">
            {shots.map((shot) => (
              <div key={shot.id} className="card p-6 border-border">
                <h3 className="font-bold text-lg mb-3">
                  SHOT {shot.id}
                  <span className="text-muted text-sm ml-auto">
                    {shot.timestamp}s
                  </span>
                </h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-muted text-sm">Scene</p>
                    <p className="font-medium">{shot.scene}</p>
                  </div>
                  <div>
                    <p className="text-muted text-sm">Action</p>
                    <p className="font-medium">{shot.action}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-muted text-sm">Subject</p>
                    <p className="font-medium">{shot.subject}</p>
                  </div>
                  <div>
                    <p className="text-muted text-sm">Environment</p>
                    <p className="font-medium">{shot.environment}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-muted text-sm">Camera</p>
                    <p className="font-medium">{shot.camera}</p>
                  </div>
                  <div>
                    <p className="text-muted text-sm">Lens</p>
                    <p className="font-medium">{shot.lens}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-muted text-sm">Lighting</p>
                    <p className="font-medium">{shot.lighting}</p>
                  </div>
                  <div>
                    <p className="text-muted text-sm">Color</p>
                    <p className="font-medium">{shot.color}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <p className="text-muted text-sm">Composition</p>
                    <p className="font-medium">{shot.composition}</p>
                  </div>
                  <div>
                    <p className="text-muted text-sm">Audio</p>
                    <p className="font-medium">{shot.audio}</p>
                  </div>
                </div>
                <div>
                  <p className="text-muted text-sm">Continuity Notes</p>
                  <p className="font-medium mt-1">{shot.continuity}</p>
                </div>
                <div className="mt-4 pt-4 border-t border-border">
                  <button className="btn-primary text-sm px-4 py-2">
                    Copy Prompt
                  </button>
                  <button className="btn-secondary text-sm px-4 py-2">
                    Export Storyboard
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </section>
  );
}