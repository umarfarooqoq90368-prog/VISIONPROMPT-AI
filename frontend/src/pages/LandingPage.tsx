import React from "react";

export default function LandingPage() {
  return (
    <section className="min-h-screen bg-bg text-fg">
      <header className="border-b border-border">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between">
          <a href="/app/analyze" className="font-semibold text-2xl tracking-tight text-accent">
            VISIONPROMPT AI
          </a>
          <nav>
            <ul className="flex gap-6 text-muted text-sm">
              <li><a href="#features" className="hover:text-accent transition-colors">Features</a></li>
              <li><a href="#how-it-works" className="hover:text-accent transition-colors">How It Works</a></li>
              <li><a href="/app/analyze" className="btn-primary text-sm px-4">Analyze Video</a></li>
            </ul>
          </nav>
        </div>
      </header>

      <main className="min-h-[80vh] px-6 py-12 flex flex-col items-center justify-center">
        <div className="text-center max-w-2xl">
          <h1 className="font-extrabold text-5xl md:text-6xl lg:text-7xl mb-6 leading-tight">
            Turn Any Video Into a Production-Ready AI Prompt
          </h1>
          <p className="mt-6 text-lg md:text-xl text-muted max-w-2xl">
            VisionPrompt AI analyzes your video's scenes, subjects, actions, camera, lens, lighting,
            color, environment, audio, and continuity to generate optimized prompts for AI video
            production.
          </p>
          <div className="mt-10 flex gap-4 flex-wrap justify-center">
            <button className="btn-primary px-8 py-3 text-lg font-medium">
              Analyze a Video
            </button>
            <button className="btn-secondary px-8 py-3 text-lg font-medium">
              Explore Features
            </button>
          </div>
        </div>
      </main>

      <section className="py-24 bg-bg-subtle" id="features">
        <div className="max-w-[1400px] mx-auto px-6">
          <h2 className="font-bold text-3xl mb-12 text-center">Features</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <div className="card p-6 hover:border-accent transition-colors">
              <h3 className="font-medium text-accent mb-2">Video-to-Video Reconstruction</h3>
              <p className="text-muted">Transform footage into optimized AI prompts</p>
            </div>
            <div className="card p-6 hover:border-accent transition-colors">
              <h3 className="font-medium text-accent mb-2">Advanced Shot Detection</h3>
              <p className="text-muted">Precise scene boundary detection</p>
            </div>
            <div className="card p-6 hover:border-accent transition-colors">
              <h3 className="font-medium text-accent mb-2">Camera & Lens Estimation</h3>
              <p className="text-muted">Focal length, FOV, lens category</p>
            </div>
            <div className="card p-6 hover:border-accent transition-colors">
              <h3 className="font-medium text-accent mb-2">Color Intelligence</h3>
              <p className="text-muted">Dominant palette extraction</p>
            </div>
            <div className="card p-6 hover:border-accent transition-colors">
              <h3 className="font-medium text-accent mb-2">Emotion & Action Analysis</h3>
              <p className="text-muted">Observed and inferred actions</p>
            </div>
            <div className="card p-6 hover:border-accent transition-colors">
              <h3 className="font-medium text-accent mb-2">Character Consistency</h3>
              <p className="text-muted">Subject tracking across frames</p>
            </div>
            <div className="card p-6 hover:border-accent transition-colors">
              <h3 className="font-medium text-accent mb-2">AI Storyboard</h3>
              <p className="text-muted">Shot-by-shot visual breakdown</p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-24 bg-bg-subtle" id="how-it-works">
        <div className="max-w-[1400px] mx-auto px-6">
          <h2 className="font-bold text-3xl mb-12 text-center">How It Works</h2>
          <div className="steps grid-cols-6 gap-2 md:grid-cols-6">
            <Step className="col-span-1">
              <span className="step-number">1</span>
              <h3>UPLOAD</h3>
              <p>Drag & drop or select your video</p>
            </Step>
            <Step className="col-span-1">
              <span className="step-number">2</span>
              <h3>ANALYZE</h3>
              <p>Backend processes frames</p>
            </Step>
            <Step className="col-span-1">
              <span className="step-number">3</span>
              <h3>UNDERSTAND</h3>
              <p>Review analysis results</p>
            </Step>
            <Step className="col-span-1">
              <span className="step-number">4</span>
              <h3>RECONSTRUCT</h3>
              <p>Generate production prompt</p>
            </Step>
            <Step className="col-span-1">
              <span className="step-number">5</span>
              <h3>GENERATE</h3>
              <p>Storyboard & quality</p>
            </Step>
            <Step className="col-span-1">
              <span className="step-number">6</span>
              <h3>EXPORT</h3>
              <p>Copy & download results</p>
            </Step>
          </div>
        </div>
      </section>

      <footer className="py-16 bg-bg-subtle">
        <div className="max-w-[1400px] mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-12">
          <div>
            <h4 className="font-bold mb-4">VisionPrompt AI</h4>
            <p className="text-muted">Turn Any Video Into a Production-Ready AI Prompt</p>
          </div>
          <div>
            <h4 className="font-bold mb-4">Product</h4>
            <ul className="text-muted text-sm">
              <li><a href="#features" className="hover:text-accent transition-colors">Features</a></li>
              <li><a href="#how-it-works" className="hover:text-accent transition-colors">How It Works</a></li>
              <li><a href="/app/analyze" className="hover:text-accent transition-colors">Analyze</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4">Company</h4>
            <ul className="text-muted text-sm">
              <li><a href="#" className="hover:text-accent transition-colors">About</a></li>
              <li><a href="#" className="hover:text-accent transition-colors">Terms</a></li>
              <li><a href="#" className="hover:text-accent transition-colors">Privacy</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4">Resources</h4>
            <ul className="text-muted text-sm">
              <li><a href="https://github.com/umarfarooqoq90368/VISIONPROMPT-AI" target="_blank" rel="noopener" className="hover:text-accent transition-colors">GitHub</a></li>
              <li><a href="#" className="hover:text-accent transition-colors">API Docs</a></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-border text-center text-muted">
          <p>VisionPrompt AI v0.1.0</p>
          <p>© 2026</p>
        </div>
      </footer>
    </section>
  );
}

function Step({children}) {
  return (
    <div className="flex flex-col items-center text-center">
      <span className="step-number rounded-full bg-accent-dim text-accent w-12 h-12 flex items-center justify-center font-bold text-sm mb-3">
        {children.props.children}
      </span>
      {children.props.children}
    </div>
  );
}