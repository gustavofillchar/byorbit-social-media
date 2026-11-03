"""Renderiza posts de notícias: python3 -I render_news.py <kit_dir> <posts.json> <out_dir>
posts.json = [{"slug", "format": "feed"|"story", "kind": "daily"|"breaking", "slides": [...]}]
Imagens: caminho relativo ao kit (ex.: ../noticias/img/x.jpg)."""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

kit = pathlib.Path(sys.argv[1]).resolve()
posts = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for post in posts:
        h = 1920 if post.get("format") == "story" else 1440
        pg = b.new_page(viewport={"width": 1080, "height": h})
        pg.goto((kit / "news.html").as_uri())
        pg.evaluate("p => window.build(p)", post)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_function("[...document.images].every(i => i.complete)")
        pg.wait_for_timeout(300)
        broken = pg.evaluate("[...document.images].filter(i => !i.naturalWidth).map(i => i.getAttribute('src'))")
        assert not broken, f"imagens não carregaram: {broken}"
        bad = pg.evaluate("""[...document.querySelectorAll('section')].filter(s=>{
            const b=s.querySelector('.body').getBoundingClientRect(),f=s.querySelector('.foot').getBoundingClientRect();
            return b.bottom > f.top-24}).map(s=>s.id)""")
        d = out / post["slug"]; d.mkdir(exist_ok=True)
        n = pg.locator("section.slide").count()
        for i in range(1, n + 1):
            pg.locator(f"#s{i}").screenshot(path=str(d / f"{post['slug']}-{i:02d}.png"))
        print(post["slug"], n, "slides", "OVERFLOW:" + ",".join(bad) if bad else "ok")
        pg.close()
    b.close()
