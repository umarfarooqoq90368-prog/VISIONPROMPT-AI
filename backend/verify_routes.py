from app.main import app
routes = [r.path for r in app.routes if hasattr(r,'path') and not r.path.startswith('/docs') and not r.path.startswith('/redoc') and not r.path.startswith('/openapi')]
for r in sorted(routes):
    print(r)
print(f"\nTotal routes: {len(routes)}")
assert '/api/videos/{stored_filename}/scenes/detect' in routes, "Day 9 route missing!"
print("Day 9 route verified: /api/videos/{stored_filename}/scenes/detect")
print("All routes verified")
