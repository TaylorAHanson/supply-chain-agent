"""User-scoped skills stored in the user's own Databricks **workspace folder**.

Every user has write access to ``/Workspace/Users/{their_email}/`` so we keep personal skills in
``/Workspace/Users/{email}/edh_agent_skills/<name>.md``. These are managed via the workspace-files
API under the user's OBO identity, listed/edited from the UI, and surfaced to the agent alongside
the shared Unity Catalog "skills" volumes.
"""

import io
import re

from databricks.sdk.service.workspace import ImportFormat, ExportFormat

USER_SKILLS_DIRNAME = "edh_agent_skills"


def safe_skill_name(name: str) -> str:
    """Normalize an arbitrary skill name into a safe filename stem (no path traversal)."""
    name = (name or "").strip()
    if name.endswith(".md"):
        name = name[:-3]
    # Collapse anything that isn't alphanumeric/dash/underscore into an underscore.
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return name[:128]


def user_skills_dir(w) -> str:
    me = w.current_user.me().user_name
    return f"/Workspace/Users/{me}/{USER_SKILLS_DIRNAME}"


def ensure_dir(w) -> str:
    d = user_skills_dir(w)
    w.workspace.mkdirs(d)
    return d


def _parse_description(content: str) -> str:
    """Pull a ``description:`` value from YAML frontmatter, if present."""
    if not content:
        return "No description provided."
    lines = content.split("\n")
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.lower().startswith("description:"):
                return line.split(":", 1)[1].strip() or "No description provided."
    return "No description provided."


def list_user_skills(w, include_content: bool = False) -> list:
    """List the user's personal skills. Returns dicts with name, description (+ content optional)."""
    d = user_skills_dir(w)
    try:
        items = list(w.workspace.list(d))
    except Exception:
        return []  # folder doesn't exist yet

    skills = []
    for obj in items:
        path = getattr(obj, "path", "") or ""
        if not path.endswith(".md"):
            continue
        name = path.rsplit("/", 1)[-1][:-3]
        content = None
        try:
            content = w.workspace.download(path, format=ExportFormat.AUTO).read().decode("utf-8")
        except Exception:
            content = ""
        entry = {"name": name, "description": _parse_description(content or "")}
        if include_content:
            entry["content"] = content or ""
        skills.append(entry)
    skills.sort(key=lambda s: s["name"].lower())
    return skills


def read_user_skill(w, name: str):
    """Return a skill's markdown content, or None if it doesn't exist."""
    stem = safe_skill_name(name)
    if not stem:
        return None
    path = f"{user_skills_dir(w)}/{stem}.md"
    try:
        return w.workspace.download(path, format=ExportFormat.AUTO).read().decode("utf-8")
    except Exception:
        return None


def write_user_skill(w, name: str, content: str) -> str:
    """Create or overwrite a user skill. Returns the workspace path written."""
    stem = safe_skill_name(name)
    if not stem:
        raise ValueError("Invalid skill name.")
    ensure_dir(w)
    path = f"{user_skills_dir(w)}/{stem}.md"
    w.workspace.upload(
        path,
        io.BytesIO((content or "").encode("utf-8")),
        format=ImportFormat.AUTO,
        overwrite=True,
    )
    return path


def delete_user_skill(w, name: str) -> bool:
    stem = safe_skill_name(name)
    if not stem:
        return False
    path = f"{user_skills_dir(w)}/{stem}.md"
    try:
        w.workspace.delete(path)
        return True
    except Exception:
        return False
