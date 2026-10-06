import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter as Router, Routes, Route, Link, Outlet } from "react-router-dom";
import "./index.css";

import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import AnalysisWorkspace from "./pages/AnalysisWorkspace";
import ShotDetection from "./pages/ShotDetection";
import CameraLens from "./pages/CameraLens";
import ColorIntelligence from "./pages/ColorIntelligence";
import EmotionAction from "./pages/EmotionAction";
import CharacterConsistency from "./pages/CharacterConsistency";
import Audio from "./pages/Audio";
import Reconstruction from "./pages/Reconstruction";
import PromptEditor from "./pages/PromptEditor";
import Storyboard from "./pages/Storyboard";
import Quality from "./pages/Quality";
import Readiness from "./pages/Readiness";
import History from "./pages/History";
import Batches from "./pages/Batches";
import Projects from "./pages/Projects";

function App() {
  return (
    <HashRouter>
      <nav className="fixed top-0 left-0 right-z-10 w-full z-50 border-b border-border bg-card/80 backdrop-blur-md">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="font-semibold text-2xl tracking-tight text-accent">
            VISIONPROMPT AI
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link to="/app/analyze" className="text-muted hover:text-accent transition-colors">Analyze Video</Link>
            <Link to="/app/reconstruction" className="text-muted hover:text-accent transition-colors">Reconstruction</Link>
            <Link to="/app/storyboard" className="text-muted hover:text-accent transition-colors">Storyboard</Link>
            <Link to="/app/quality" className="text-muted hover:text-accent transition-colors">Quality</Link>
            <Link to="/app/readiness" className="text-muted hover:text-accent transition-colors">Readiness</Link>
            <Link to="/app/history" className="text-muted hover:text-accent transition-colors">History</Link>
            <Link to="/app/batches" className="text-muted hover:text-accent transition-colors">Batches</Link>
            <Link to="/app/projects" className="text-muted hover:text-accent transition-colors">Projects</Link>
          </div>
        </div>
      </nav>

      <main className="mt-20 px-6 pb-12">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/app/analyze" element={<AnalysisWorkspace />} />
          <Route path="/app/reconstruction" element={<Reconstruction />} />
          <Route path="/app/storyboard" element={<Storyboard />} />
          <Route path="/app/prompt" element={<PromptEditor />} />
          <Route path="/app/quality" element={<Quality />} />
          <Route path="/app/readiness" element={<Readiness />} />
          <Route path="/app/history" element={<History />} />
          <Route path="/app/batches" element={<Batches />} />
          <Route path="/app/projects" element={<Projects />} />
          <Route path="/app" element={<Dashboard />} />
        </Routes>
      </main>
    </HashRouter>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<React.StrictMode><App /></React.StrictMode>);