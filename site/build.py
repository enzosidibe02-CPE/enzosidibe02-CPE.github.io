"""Build the static portfolio site into site/dist.

    python site/build.py

Reads ../content/content.json, renders Jinja2 templates, copies static assets and the
résumé PDFs (build them first with resume/build_resume.py). No runtime dependencies in
the output: plain HTML, one CSS file, one small JS file.

Requires: Jinja2, Pillow (for image dimensions).
"""
import json
import os
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = HERE / "dist"
SVG_SIZES = {"ev_sense_circuit.svg": (640, 270)}


def image_size(name: str):
    if name in SVG_SIZES:
        return SVG_SIZES[name]
    with Image.open(HERE / "static/img" / name) as im:
        return im.size


def main() -> int:
    content_path = Path(os.environ.get("PORTFOLIO_CONTENT", ROOT / "content/content.json"))
    data = json.loads(content_path.read_text(encoding="utf-8"))
    person = data["person"]

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "projects").mkdir(parents=True)
    shutil.copytree(HERE / "static", DIST / "static")
    (DIST / ".nojekyll").write_text("")

    # résumé PDFs (optional: omitted when the content file has no "resume" block)
    resume_files = []
    for key, v in data.get("resume", {}).get("versions", {}).items():
        src = ROOT / "resume/out" / f"{v['file']}.pdf"
        if not src.exists():
            print(f"missing {src}: run resume/build_resume.py first", file=sys.stderr)
            return 1
        (DIST / "assets").mkdir(exist_ok=True)
        shutil.copy(src, DIST / "assets" / src.name)
        resume_files.append(dict(href=f"assets/{src.name}", label=f"{v['headline']} (PDF)"))

    projects = data["projects"]
    for p in projects:
        for im in p["images"]:
            im["w"], im["h"] = image_size(im["src"])
        repo = p["repo"]
        p["repo_url"] = f"{person['github_url']}/{repo['name']}" if repo["status"] == "published" else None

    env = Environment(loader=FileSystemLoader(str(HERE / "templates")), autoescape=select_autoescape(["html"]))
    common = dict(person=person, headline=data["headline"], tagline=data["tagline"])

    index = env.get_template("index.html").render(
        root="", current="home", page_title="", description=data["tagline"],
        about=data["about"], projects=projects, skills=data["skills"], education=data["education"],
        resume_files=resume_files, **common,
    )
    (DIST / "index.html").write_text(index, encoding="utf-8")

    tpl = env.get_template("project.html")
    for i, p in enumerate(projects):
        html = tpl.render(
            root="../", current="project", page_title=p["title"], description=p["tagline"], p=p, resume_files=resume_files,
            prev=projects[i - 1] if i > 0 else None, next=projects[i + 1] if i + 1 < len(projects) else None,
            **common,
        )
        (DIST / "projects" / f"{p['slug']}.html").write_text(html, encoding="utf-8")

    (HERE / "static/favicon.svg").exists() or print("note: no favicon.svg", file=sys.stderr)
    n = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"built {n} files into {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
