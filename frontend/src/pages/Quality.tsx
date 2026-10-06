import React from "react";

const Quality: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-4">Quality</h1>
      <p className="text-muted">Quality assessment page</p>
      <div className="mt-6">
        <a to="/app/analyze" className="text-muted hover:text-accent transition-colors block">
          Analyze Video
        </a>
        <a to="/app/reconstruction" className="text-muted hover:text-accent transition-colors block">
          Reconstruction
        </a>
        <a to="/app/storyboard" className="text-muted hover:text-accent transition-colors block">
          Storyboard
        </a>
        <a to="/app/quality" className="text-muted hover:text-accent transition-colors block">
          Quality
        </a>
      </div>
    </div>
  );
};

export default Quality;