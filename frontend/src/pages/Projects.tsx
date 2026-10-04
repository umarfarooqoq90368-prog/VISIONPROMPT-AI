import React, { useState } from "react";

export default function Projects() {
  const [projects, setProjects] = useState<
    { id: number; name: string; description: string; videoCount: number }[]
  >([]);
  const [newProject, setNewProject] = useState<string>("");

  const handleAddProject = () => {
    if (!newProject.trim()) return;
    const project = {
      id: projects.length + 1,
      name: newProject,
      description: "",
      videoCount: 0,
    };
    setProjects([...projects, project]);
    setNewProject("");
  };

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
                to "/app/quality"
                className="text-muted hover:text-accent transition-colors block px-4 py-2 rounded"
              >
                Quality
              </a>
            </li>
          </ul>
        </nav>
      </aside>

      <main className="ml-64 p-6 flex-1">
        <div className="max-w-2xl mx-auto">

          {/* Create Project form */}
          <div className="card p-6 mb-8">
            <h2 className="font-bold text-2xl mb-4">Projects</h2>
            <p className="text-muted mb-4">
              Organize your videos and analyses.
            </p>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <input
                value={newProject}
                onChange={(e) => setNewProject(e.target.value)}
                className="border rounded border-border px-3 py-2 focus:outline-none focus:border-accent"
                placeholder="Project name"
              />
              <button
                onClick={handleAddProject}
                className="btn-primary px-4 py-2"
              >
                Create
              </button>
            </div>
          </div>

          {/* Projects list */}
          {projects.length > 0 ? (
            <div>
              <h3 className="font-bold text-lg mb-4">Your Projects</h3>
              <ul className="space-y-3 text-muted">
                {projects.map((project) => (
                  <li key={project.id}>
                    <strong>{project.name}</strong>
                    <span className="text-muted/2 ml-2">({project.videoCount} videos)</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-muted">
              No projects yet. Create your first project above.
            </p>
          )}
        </div>
      </main>
    </section>
  );
}