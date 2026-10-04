import React from "react";

export default function ColorIntelligence() {
  // Sample color data
  const colors = [
    { hex: "#00d4aa", rgb: "0, 212, 170", percentage: "35%", brightness: "High", saturation: "Vibrant" },
    { hex: "#1a1a24", rgb: "26, 26, 36", percentage: "28%", brightness: "Low", saturation: "Muted" },
    { hex: "#2d3748", rgb: "45, 55, 72", percentage: "22%", brightness: "Low", saturation: "Muted" },
    { hex: "#4a5568", rgb: "74, 85, 104", percentage: "15%", brightness: "Medium", saturation: "Muted" },
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
            <h2 className="font-bold text-2xl mb-4">Color Intelligence</h2>
            <p className="text-muted">
              Using P2-04 color palette extraction.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            
            {/* Dominant Colors */}
            <div>
              <h4 className="font-bold text-lg mb-4">Dominant Colors</h4>
              <div className="space-y-4">
                {colors.map((color, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div
                      className={`
                        w-12 h-8 rounded
                        bg-${color.hex.replace("#", "")}
                        flex-shr-0
                      `}
                    ></div>
                    <div>
                      <p className="font-medium">{color.hex}</p>
                      <p className="text-xs text-muted">{color.rgb}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Color Details */}
            <div>
              <h4 className="font-bold text-lg mb-4">Color Details</h4>
              <p className="text-muted mb-2">
                Brightness: {colors[0]?.brightness || "High"}
              </p>
              <p className="text-muted mb-2">
                Saturation: {colors[0]?.saturation || "Vibrant"}
              </p>
              <p className="text-muted mb-3">
                Temperature: Cool (dominant teal/cyan hues)
              </p>
              <p className="text-muted text-sm">
                Visual mood: Cinematic, cool-toned atmosphere
              </p>
            </div>
          </div>

          <div className="mt-8">
            <button
              className="btn-primary px-6 py-3"
              disabled
            >
              Copy HEX Colors
            </button>
            <p className="text-muted/2 mt-2">
              Copied to clipboard. Provider: Heuristic (P2-04).
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}