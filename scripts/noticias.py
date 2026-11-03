"""Robô de notícias da ByOrbit (Tech News e Breaking).

  python scripts/noticias.py daily    [--dry-run]   # carrossel Tech News do dia
  python scripts/noticias.py breaking [--dry-run]   # verifica se há breaking e publica feed + story

Secrets: ANTHROPIC_API_KEY, UNSPLASH_ACCESS_KEY, IG_TOKEN, IG_USER_ID.
Fluxo: RSS de portais internacionais -> Claude escolhe/traduz/resume -> foto do Unsplash ->
render (kit/news.html) -> JPEG no repositório -> API do Instagram.
Tudo o que foi publicado fica em noticias/publicadas.json (para não repetir).
"""
import argparse, datetime, email.utils, html, json, os, re, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ig_publish  # noqa: E402  (api, wait_ready)

TZ = ZoneInfo("America/Sao_Paulo")
NOW = datetime.datetime.now(TZ)
RAW = "https://raw.githubusercontent.com/gustavofillchar/byorbit-social-media/main/"
LOG = os.path.join(ROOT, "noticias", "publicadas.json")
MODEL = os.environ.get("NEWS_MODEL", "claude-sonnet-5-5")
UA = "Mozilla/5.0 (compatible; ByOrbitNewsBot/1.0; +https://www.byorbit.space)"

FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Wired": "https://www.wired.com/feed/rss",
    "Engadget": "https://www.engadget.com/rss.xml",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
}

REGRAS = """Você é o editor do "Tech News", a seção de notícias de tecnologia do Instagram da ByOrbit,
uma software house brasileira. O público são donos de empresa e gestores brasileiros, não técnicos.
Regras obrigatórias:
- Escreva em português do Brasil, com suas próprias palavras. Nunca copie frases do original.
- Use SOMENTE fatos presentes no texto fornecido. Não invente números, datas, nomes ou citações.
  Se um número não estiver no texto, não use número.
- Mantenha nomes próprios de empresas e produtos como no original.
- Evite política partidária, eleições, guerra, violência, mortes e temas sensíveis. Prefira IA, big techs,
  startups, segurança digital, produtos, chips, negócios e regulação de tecnologia.
- Tom direto e neutro, sem sensacionalismo e sem emoji.
- image_query: 2 a 4 palavras em INGLÊS descrevendo objetos ou lugares genéricos que ilustrem o tema
  (ex.: "smartwatch wrist", "server room", "microchip closeup"). Nunca pessoas, rostos, logos ou marcas.
Responda apenas com JSON válido entre <json> e </json>."""


def log(msg):
    print(f"[{datetime.datetime.now(TZ):%H:%M:%S}] {msg}", flush=True)


def http(url, data=None, headers=None, timeout=40):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------- coleta ----------
def parse_date(txt):
    if not txt:
        return None
    try:
        d = email.utils.parsedate_to_datetime(txt)
    except Exception:
        try:
            d = datetime.datetime.fromisoformat(txt.replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def strip(txt):
    txt = re.sub(r"<[^>]+>", " ", html.unescape(txt or ""))
    return re.sub(r"\s+", " ", txt).strip()


def collect(hours):
    since = NOW - datetime.timedelta(hours=hours)
    items = []
    for source, url in FEEDS.items():
        try:
            root = ET.fromstring(http(url))
        except Exception as e:
            log(f"feed {source} falhou: {e}")
            continue
        for it in root.iter():
            tag = it.tag.split("}")[-1]
            if tag not in ("item", "entry"):
                continue
            get = lambda n: next((c for c in it if c.tag.split("}")[-1] == n), None)
            title = strip(getattr(get("title"), "text", ""))
            link_el = get("link")
            link = (link_el.get("href") or link_el.text) if link_el is not None else ""
            date = parse_date(getattr(get("pubDate"), "text", None) or getattr(get("published"), "text", None)
                              or getattr(get("updated"), "text", None))
            summary = strip(getattr(get("description"), "text", None) or getattr(get("summary"), "text", ""))[:400]
            if title and link and date and date >= since:
                items.append({"source": source, "title": title, "link": link.strip(),
                              "date": date.astimezone(TZ).strftime("%d/%m/%Y"), "summary": summary})
    log(f"{len(items)} notícias nas últimas {hours}h")
    return items


def article_text(url):
    try:
        raw = http(url).decode("utf-8", "replace")
    except Exception as e:
        return f"(não foi possível abrir o artigo: {e})"
    raw = re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", raw)
    paras = [strip(p) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", raw)]
    text = " ".join(p for p in paras if len(p) > 60)
    return text[:7000] or "(sem texto extraído)"


# ---------- Claude ----------
def claude(prompt, max_tokens=16000):
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens, "system": REGRAS,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for attempt in range(3):
        r, text = {}, ""
        try:
            r = json.loads(http("https://api.anthropic.com/v1/messages", data=body, timeout=180, headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                "content-type": "application/json"}))
            text = "".join(b.get("text", "") for b in r.get("content", []))
            m = re.search(r"<json>(.*?)</json>", text, re.S)
            chunk = m.group(1) if m else text
            chunk = chunk[chunk.find("{"):chunk.rfind("}") + 1]
            return json.loads(chunk)
        except urllib.error.HTTPError as e:
            log(f"API Anthropic erro {e.code}: {e.read().decode()[:300]}")
        except Exception as e:
            log(f"resposta da API inválida: {e} | stop={r.get('stop_reason')} | início: {(text or str(r))[:300]!r}")
        time.sleep(10)
    sys.exit("Não consegui uma resposta válida da API da Anthropic")


def listing(items):
    return "\n".join(f"[{i}] {it['source']} ({it['date']}): {it['title']} — {it['summary'][:220]}"
                     for i, it in enumerate(items))


# ---------- imagens (Unsplash) ----------
def unsplash(query, dest):
    key = os.environ["UNSPLASH_ACCESS_KEY"]
    q = urllib.parse.urlencode({"query": query, "orientation": "landscape", "content_filter": "high", "per_page": 10})
    res = json.loads(http(f"https://api.unsplash.com/search/photos?{q}",
                          headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"}))["results"]
    used = set(json.load(open(LOG)).get("_fotos", [])) if os.path.exists(LOG) else set()
    res = [r for r in res if r["id"] not in used] or res
    if not res:
        return None
    ph = res[0]
    try:  # exigência da API do Unsplash: registrar o download
        http(ph["links"]["download_location"], headers={"Authorization": f"Client-ID {key}"})
    except Exception:
        pass
    open(dest, "wb").write(http(ph["urls"]["regular"]))
    return {"id": ph["id"], "credit": f"Foto: {ph['user']['name']} / Unsplash"}


def fallback_query(q):
    return "technology abstract" if q != "technology abstract" else "computer chip"


# ---------- render ----------
def render(posts, outdir):
    path = os.path.join(ROOT, "noticias", "_render.json")
    json.dump(posts, open(path, "w"), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "kit", "render_news.py"), os.path.join(ROOT, "kit"),
                        path, outdir], capture_output=True, text=True)
    os.remove(path)
    print(r.stdout, r.stderr)
    if r.returncode:
        sys.exit("Falha ao renderizar as artes")
    return "OVERFLOW" not in r.stdout


def to_jpegs(folder):
    from PIL import Image
    out = []
    for f in sorted(os.listdir(folder)):
        if f.endswith(".png"):
            jpg = os.path.join(folder, f[:-4] + ".jpg")
            Image.open(os.path.join(folder, f)).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True)
            out.append(jpg)
    return out


def git_push(msg):
    subprocess.run(["git", "add", "noticias"], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    subprocess.run(["git", "commit", "-qm", msg], cwd=ROOT, check=True)
    for _ in range(3):
        subprocess.run(["git", "pull", "--rebase", "-q"], cwd=ROOT)
        if subprocess.run(["git", "push", "-q"], cwd=ROOT).returncode == 0:
            time.sleep(30)  # dá tempo de o raw.githubusercontent servir os arquivos novos
            return
    sys.exit("git push falhou")


def url(path):
    return RAW + os.path.relpath(path, ROOT)


# ---------- Instagram ----------
def ig_carousel(jpgs, caption):
    uid = os.environ["IG_USER_ID"]
    kids = [ig_publish.api("POST", f"{uid}/media", image_url=url(j), is_carousel_item="true")["id"] for j in jpgs]
    for k in kids:
        ig_publish.wait_ready(k)
    c = ig_publish.api("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    ig_publish.wait_ready(c)
    return c


def ig_single(jpg, caption=None, story=False):
    uid = os.environ["IG_USER_ID"]
    params = {"image_url": url(jpg)}
    if story:
        params["media_type"] = "STORIES"
    else:
        params["caption"] = caption
    c = ig_publish.api("POST", f"{uid}/media", **params)["id"]
    ig_publish.wait_ready(c)
    return c


def ig_go(container):
    uid = os.environ["IG_USER_ID"]
    mid = ig_publish.api("POST", f"{uid}/media_publish", creation_id=container)["id"]
    return ig_publish.api("GET", mid, fields="permalink").get("permalink", "")


# ---------- registro ----------
def load_log():
    return json.load(open(LOG)) if os.path.exists(LOG) else {"daily": {}, "breaking": [], "links": [], "titulos": [], "_fotos": []}


def save_log(d):
    json.dump(d, open(LOG, "w"), indent=1, ensure_ascii=False)


# ---------- montagem ----------
def write_news(chosen, mode, extra=""):
    blocos = "\n\n".join(f"### Notícia {i}\nFonte: {it['source']} ({it['date']})\nLink: {it['link']}\n"
                         f"Título original: {it['title']}\nTexto:\n{article_text(it['link'])}"
                         for i, it in enumerate(chosen))
    formato = """{"news":[{"company":"NOME DA EMPRESA principal (curto, ex.: Apple, OpenAI, Nvidia)",
 "title":"manchete em pt-BR com 6 a 11 palavras, com UMA expressão-chave entre <span class=\\"blue\\"> e </span>",
 "short":"versão da manchete com até 8 palavras, sem HTML",
 "body":"resumo em 2 frases, 28 a 38 palavras, só com fatos do texto",
 "image_query":"...", "source":"nome do portal", "source_date":"DD/MM/AAAA", "link":"..."}]"""
    if mode == "daily":
        formato += """, "caption":"legenda do carrossel: 1 linha de abertura, lista numerada com as manchetes, uma pergunta para
 comentários, a linha 'Fontes: ...' com os portais e datas, a linha 'Fotos ilustrativas: Unsplash.', a linha 'Quer levar IA
 ou tecnologia para a sua empresa? Inicie seu briefing pelo link na bio. A ByOrbit responde em até 24h.' e 5 hashtags em
 português no fim"}"""
    else:
        formato += """, "caption":"legenda do breaking: 2 a 3 parágrafos curtos explicando o que aconteceu e por que importa
 para empresas, a linha 'Fonte: portal (data)', a linha 'Foto ilustrativa: Unsplash.' e 4 hashtags em português"}"""
    return claude(f"Escreva {len(chosen)} notícia(s) para o Instagram, na mesma ordem.{extra}\n\nFormato:\n{formato}\n\n{blocos}")


def build_posts(data, mode, slug_base):
    imgdir = os.path.join(ROOT, "noticias", "img")
    os.makedirs(imgdir, exist_ok=True)
    fotos, slides = [], []
    for i, n in enumerate(data["news"]):
        dest = os.path.join(imgdir, f"{slug_base}-{i + 1}.jpg")
        ph = unsplash(n["image_query"], dest) or unsplash(fallback_query(n["image_query"]), dest)
        if not ph:
            sys.exit(f"Sem foto para '{n['image_query']}'")
        fotos.append(ph["id"])
        slides.append({"type": "news", "company": n["company"], "title": n["title"], "body": n["body"],
                       "image": f"../noticias/img/{os.path.basename(dest)}", "credit": ph["credit"],
                       "source": n["source"], "sourceDate": n["source_date"]})
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
             "outubro", "novembro", "dezembro"]
    if mode == "daily":
        cover = {"type": "cover", "title": "Tech News", "date": f"{NOW.day:02d} de {meses[NOW.month - 1]} de {NOW.year}",
                 "items": [n["short"] for n in data["news"]]}
        end = {"type": "end", "title": "Tecnologia descomplicada, todo dia.",
               "body": "As principais notícias de tecnologia, direto ao ponto.<br>"
                       "Quer levar IA para a sua empresa? A ByOrbit responde em até 24h."}
        posts = [{"slug": slug_base, "format": "feed", "kind": "daily", "slides": [cover, *slides, end]}]
    else:
        posts = [{"slug": slug_base + "-feed", "format": "feed", "kind": "breaking", "slides": slides[:1]},
                 {"slug": slug_base + "-story", "format": "story", "kind": "breaking", "slides": slides[:1]}]
    return posts, fotos


def produce(chosen, mode, slug_base):
    outdir = os.path.join(ROOT, "noticias", "posts")
    data = write_news(chosen, mode)
    posts, fotos = build_posts(data, mode, slug_base)
    if not render(posts, outdir):
        log("texto passou do espaço; pedindo versão mais curta")
        data = write_news(chosen, mode, " IMPORTANTE: seja mais curto: manchete com até 8 palavras e resumo com até 26 palavras.")
        posts, fotos = build_posts(data, mode, slug_base)
        if not render(posts, outdir):
            sys.exit("Texto continua grande demais para o template")
    folders = [os.path.join(outdir, p["slug"]) for p in posts]
    return data, folders, fotos


def run_daily(dry):
    reg = load_log()
    key = NOW.strftime("%Y-%m-%d")
    if key in reg["daily"] and not dry:
        log("Tech News de hoje já publicado.")
        return
    items = [i for i in collect(30) if i["link"] not in reg["links"]]
    if len(items) < 4:
        sys.exit("Poucas notícias novas nos feeds")
    ja = "\n".join(reg.get("titulos", [])[-40:]) or "(nenhum)"
    pick = claude("Escolha as 4 notícias mais relevantes e variadas para o público (assuntos diferentes, sem duas "
                  "sobre o mesmo fato). NÃO escolha nenhum fato já publicado nos últimos dias, mesmo que venha de "
                  "outro portal:\n" + ja + "\n\nFormato: {\"escolhidas\":[índices]}\n\n" + listing(items[:80]), 8000)
    chosen = [items[i] for i in pick["escolhidas"][:4]]
    data, folders, fotos = produce(chosen, "daily", f"tech-news-{key}")
    jpgs = to_jpegs(folders[0])
    git_push(f"Tech News {key}" + (" (teste)" if dry else ""))
    if dry:
        log("TESTE: artes geradas e salvas em noticias/posts/, nada publicado.")
        return
    link = ig_go(ig_carousel(jpgs, data["caption"]))
    reg["daily"][key] = link
    reg["links"] += [c["link"] for c in chosen]
    reg.setdefault("titulos", []).extend(n["short"] for n in data["news"])
    reg["_fotos"] += fotos
    save_log(reg)
    git_push(f"Registro Tech News {key}")
    log(f"Publicado: {link}")


def run_breaking(dry):
    reg = load_log()
    today = NOW.strftime("%Y-%m-%d")
    if sum(1 for b in reg["breaking"] if b["date"] == today) >= 2 and not dry:
        log("Já houve 2 breakings hoje. Nada a fazer.")
        return
    items = [i for i in collect(4) if i["link"] not in reg["links"]]
    if not items:
        log("Nenhuma notícia nova.")
        return
    recentes = "\n".join(reg.get("titulos", [])[-40:])
    d = claude("Decida se alguma destas notícias das últimas horas é um BREAKING de verdade: um fato grande, novo e "
               "relevante para empresas (ex.: lançamento muito importante, aquisição bilionária, falha ou ataque que "
               "afeta milhões, mudança regulatória grande). Ele PRECISA aparecer em pelo menos 2 portais diferentes da "
               "lista. Na dúvida, responda que não. Não repita assuntos já publicados:\n" + (recentes or "(nenhum)") +
               "\n\nFormato: {\"breaking\": true|false, \"indices\": [índices das matérias sobre o fato, de portais "
               "diferentes], \"motivo\": \"...\"}\n\n" + listing(items[:80]), 8000)
    log(f"Avaliação: {d}")
    idx = d.get("indices") or []
    if not d.get("breaking") or len({items[i]["source"] for i in idx if i < len(items)}) < 2:
        log("Sem breaking agora.")
        return
    chosen = [items[idx[0]]]
    slug = f"breaking-{NOW:%Y-%m-%d-%H%M}"
    data, folders, fotos = produce(chosen, "breaking", slug)
    feed_jpg, story_jpg = to_jpegs(folders[0])[0], to_jpegs(folders[1])[0]
    git_push(f"Breaking {slug}" + (" (teste)" if dry else ""))
    if dry:
        log("TESTE: breaking gerado e salvo em noticias/posts/, nada publicado.")
        return
    link = ig_go(ig_single(feed_jpg, caption=data["caption"]))
    try:
        ig_go(ig_single(story_jpg, story=True))
    except SystemExit as e:
        log(f"Story falhou (feed publicado): {e}")
    reg["breaking"].append({"date": today, "title": data["news"][0]["short"], "link": link})
    reg.setdefault("titulos", []).append(data["news"][0]["short"])
    reg["links"] += [items[i]["link"] for i in idx if i < len(items)]
    reg["_fotos"] += fotos
    save_log(reg)
    git_push(f"Registro {slug}")
    log(f"Breaking publicado: {link}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["daily", "breaking"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    (run_daily if a.mode == "daily" else run_breaking)(a.dry_run)
