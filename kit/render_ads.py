"""Renderiza criativos de anúncio (sob demanda, fora do robô de publicação):
python3 -I kit/render_ads.py kit anuncios/<arquivo>.json anuncios/
ads.json = [{"slug", "format": "feed"|"story", "label", "slides": [...]}]  (tipos em kit/ads.html)
feed = 1080x1350 (4:5) · story = 1080x1920 (9:16)
Imagens de fundo: caminho relativo ao kit (ex.: ../noticias/img/x.jpg)."""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

kit = pathlib.Path(sys.argv[1]).resolve()
ads = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for ad in ads:
        h = 1920 if ad.get("format") == "story" else 1350
        pg = b.new_page(viewport={"width": 1080, "height": h})
        pg.goto((kit / "ads.html").as_uri())
        pg.evaluate("document.fonts.ready")
        pg.evaluate("p => window.build(p)", ad)
        pg.wait_for_function("[...document.images].every(i => i.complete)")
        pg.wait_for_timeout(400)
        fonts = pg.evaluate("[...document.fonts].filter(f=>f.status==='loaded').length")
        assert fonts >= 4, f"fontes Geist não carregaram ({fonts}); baixe para kit/fonts/"
        broken = pg.evaluate("[...document.images].filter(i => !i.naturalWidth).map(i => i.getAttribute('src'))")
        assert not broken, f"imagens não carregaram: {broken}"
        # conteúdo não pode encostar na barra de chamada
        bad = pg.evaluate("""[...document.querySelectorAll('section')].filter(s=>{
            const c=s.querySelector('.ctabar').getBoundingClientRect();
            const els=[...s.querySelectorAll('.hl,.split,.stbody,.fc')];
            return els.some(e=>e.getBoundingClientRect().bottom > c.top-16)}).map(s=>s.id)""")
        d = out / ad["slug"]; d.mkdir(exist_ok=True)
        n = pg.locator("section.slide").count()
        for i in range(1, n + 1):
            name = ad["slug"] + (f"-{i:02d}" if n > 1 else "") + ".png"
            pg.locator(f"#s{i}").screenshot(path=str(d / name))
        print(ad["slug"], n, "arte(s)", "OVERFLOW:" + ",".join(bad) if bad else "ok")
        pg.close()
    b.close()
