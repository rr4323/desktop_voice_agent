"""Path resolution for newly-*created* files.

Every read/write tool operates on files the caller already named an
absolute (or resolvable) path for — those come from context.open_files,
supplied by the frontend. "create" operations are different: the planner
may propose a bare filename (e.g. "rr.pptx") for something that doesn't
exist yet anywhere. This resolves that bare filename against a fixed
workspace directory rather than the server process's cwd, so created files
land somewhere predictable regardless of how/where the server was started.
"""
import os

WORKSPACE_DIR = os.path.expanduser(os.environ.get("WORKSPACE_DIR", "~/agent_workspace"))


def resolve(path: str) -> str:
    """Absolute paths pass through unchanged; bare filenames are placed
    under WORKSPACE_DIR (created if it doesn't exist yet)."""
    if os.path.isabs(path):
        return path
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    return os.path.join(WORKSPACE_DIR, path)
