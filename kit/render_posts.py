"""Render ByOrbit carousels: python3 -I render_posts.py <kit_dir> <posts.json> <out_dir>
posts.json = [{"slug": "...", "slides": [...]}, ...]  (see template.html for slide types)"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

kit = pathlib.Path(sys.argv[1]).resolve()
posts = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1440})
    pg.goto((kit / "template.html").as_uri())
    for post in posts:
        pg.evaluate("p => window.build(p)", post)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(300)
        fonts = pg.evaluate("[...document.fonts].filter(f=>f.status==='loaded').length")
        assert fonts >= 4, f"fontes Geist não carregaram ({fonts})"
        # overflow guard: content block must stay clear of header and footer
        bad = pg.evaluate("""[...document.querySelectorAll('section')].filter(s=>{
            const b=s.querySelector('.body').getBoundingClientRect(),h=s.querySelector('.head').getBoundingClientRect(),f=s.querySelector('.foot').getBoundingClientRect();
            return b.top < h.bottom+60 || b.bottom > f.top-20 || s.querySelector('.body').scrollWidth > b.width+2}).map(s=>s.id)""")
        d = out / post["slug"]; d.mkdir(exist_ok=True)
        n = pg.locator("section.slide").count()
        for i in range(1, n + 1):
            pg.locator(f"#s{i}").screenshot(path=str(d / f"{post['slug']}-{i:02d}.png"))
        print(post["slug"], n, "slides", "OVERFLOW:" + ",".join(bad) if bad else "ok")
    b.close()
