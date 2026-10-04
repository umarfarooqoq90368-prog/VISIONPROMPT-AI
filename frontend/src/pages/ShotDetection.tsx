import React from "react";

export default function ShotDetection() {
  // Sample shot data from P2-02 API
  const shots = [
    {
      id: 1,
      startTime: 0.0,
      endTime: 8.5,
      duration: 8.5,
      transition: "cut",
      shotType: "change",
      confidence: 0.95,
      representativeFrame: "",
    },
    {
      id: 2,
      startTime: 8.5,
      endTime: 15.2,
      duration: 6.7,
      transition: "fade",
      shotType: "within-scene",
      confidence: 0.88,
      representativeFrame: "",
    },
    {
      id: 3,
      startTime: 15.2,
      endTime: 22.0,
      duration: 6.8,
      transition: "cut",
      shotType: "change",
      confidence: 0.92,
      representativeFrame: "",
    },
    {
      id: 4,
      startTime: 22.0,
      endTime: 28.5,
      duration: 6.5,
      transition: "dissolve",
      shotType: "within-scene",
      confidence: 0.85,
      representativeFrame: "",
    },
    {
      id: 5,
      startTime: 28.5,
      endTime: 35.0,
      duration: 6.5,
      transition: "cut",
      shotType: "change",
      confidence: 0.96,
      representativeFrame: "",
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
            <li>
              <a
                to="/app/readiness"
                className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
              >
                Readiness
              </a>
            </li>
            <li>
              <a
                to="/app/history"
                className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
              >
                History
              </a>
            </li>
          </ul>
        </nav>
      </aside>

      <main className="ml-64 p-6 flex-1">
        <div className="max-w-7xl mx-auto">

          {/* Header */}
          <div className="card p-6 mb-8">
            <h2 className="font-bold text-2xl mb-4">Shot Detection</h2>
            <p className="text-muted">
              Heuristic shot boundary detection using P2-02 analysis.
            </p>
          </div>

          {/* Shots Timeline */}
          <div className="card p-6">
            <h3 className="font-bold text-xl mb-4">Detected Shots</h3>
            <p className="text-muted/2 text-sm mb-6">
              5 scenes detected using heuristic analysis.
            </p>

            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left text-sm font-medium text-muted px-6 py-3">Shot</th>
                    <th className="text-left text-sm font-medium text-muted px-6 py-3">Start</th>
                    <th className="text-left text-sm font-medium text-muted px-6 py-3">End</th>
                    <th className="text-left text-sm font-medium text-muted px-6 py-3">Duration</th>
                    <th className="text-left text-sm font-medium text-muted px-6 py-3">Transition</th>
                    <th className="text-left text-sm font-medium text-muted px-6 py-3">Type</th>
                    <th className="text-left text-sm font-medium text-muted px-6 py-3">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {shots.map((shot) => (
                    <tr key={shot.id} className="border-b border-border">
                      <td className="text-left px-6 py-4 font-medium">
                        {shot.id}
                      </td>
                      <td className="text-left px-6 py-4">
                        {shot.startTime}s
                      </td>
                      <td className="text-left px-6 py-4">
                        {shot.endTime}s
                      </td>
                      <td className="text-left px-6 py-4">
                        {shot.duration}s
                      </td>
                      <td className="text-left px-6 py-4">
                        {shot.transition}
                      </td>
                      <td className="text-left px-6 py-4">
                        {shot.shotType}
                      </td>
                      <td className="text-left px-6 py-4">
                        {shot.confidence > 0.9
                          ? "HIGH"
                          : shot.confidence > 0.7
                            ? "MEDIUM"
                            : "LOW"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Shot details */}
          <div className="mt-8">
            <h3 className="font-bold text-xl mb-4">Shot Details</h3>
            <p className="text-muted">
              Click a shot from the table above to inspect its details.
            </p>
            <p className="text-muted/2">
              Provider: Heuristic (P2-02). No AI model inference claimed.
            </p>
          </div>
        </div>
      </main>
    </section>
  );
}