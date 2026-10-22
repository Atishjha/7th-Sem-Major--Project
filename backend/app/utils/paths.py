"""
Where data/ and ml/ live, independent of how the app is launched.

The old approach (`Path(__file__).parents[3]`) only worked in a source
checkout. In the Docker image the code lives at /app/app/..., so
parents[3] is "/" — uploads and trained models silently landed in the
container's own throwaway filesystem instead of the ./data and ./ml
folders mounted from the host.

Resolution order:
  1. PROJECT_ROOT environment variable, if set.
  2. The nearest ancestor of this file that contains a data/ directory
     (the repo root in a checkout; /app in Docker, where compose mounts
     ./data at /app/data).
  3. Fallback: the directory holding the `app` package.
"""
import os
from pathlib import Path
def project_root() -> Path:
    override = os.environ.get("PROJECT_ROOT")
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data").is_dir():
            return parent
    return here.parents[2]
