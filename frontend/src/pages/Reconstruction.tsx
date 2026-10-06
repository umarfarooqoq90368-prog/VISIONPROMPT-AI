import React from "react";

const Reconstruction: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-4">Reconstruction</h1>
      <p className="text-muted">3D reconstruction and view synthesis</p>
      <nav className="mt-6">
        <ul className="space-y-2 p-4">
          <li>
            <a to="/app/analyze" className="text-muted hover:text-accent transition-colors block">
              Analyze Video
            </a>
          </li>
          <li>
            <a to="/app/reconstruction" className="text-muted hover:text-accent transition-colors block">
              Reconstruction
            </a>
          </li>
          <li>
            <a to="/app/storyboard" className="text-muted hover:text-accent transition-colors block">
              Storyboard
            </a>
          </li>
          <li>
            <a to="/app/quality" className="text-muted hover:text-accent transition-colors block">
              Quality
            </a>
          </li>
          <li>
            <a to="/app/readiness" className="text-muted hover:text-accent transition-colors block">
              Readiness
            </a>
          </li>
        </ul>
      </nav>
    </div>
  );
};

export default Reconstruction;