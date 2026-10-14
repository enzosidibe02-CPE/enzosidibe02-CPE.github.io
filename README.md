# Portfolio website

Source for https://enzosidibe02-cpe.github.io: a static site (plain HTML, one CSS file, one small JavaScript file). Text comes from `content/content.json`; `site/build.py` renders it with Jinja2 into `site/dist/`, and `site/check_site.py` checks links, anchors, alt text, headings and shipped files before each deploy.

```bash
pip install -r site/requirements.txt
python site/build.py
python site/check_site.py
python -m http.server 8000 --directory site/dist
```

Deployed with GitHub Pages through `.github/workflows/pages.yml`.

The text, figures and code of this site were prepared with AI assistance (Claude); the projects described are the author's coursework and team work. Each project page states what was measured, what was modeled or simulated, and what could not be verified.
