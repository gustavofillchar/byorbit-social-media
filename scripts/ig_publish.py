"""Publica no Instagram o carrossel do dia, pela API oficial (sem Metricool).

Uso:
  python scripts/ig_publish.py prepare  [--date AAAA-MM-DD]   # gera os JPEGs do post do dia
  python scripts/ig_publish.py publish  [--date AAAA-MM-DD] [--dry-run]

Variáveis de ambiente (GitHub Secrets): IG_TOKEN, IG_USER_ID.
O post do dia é procurado em posts/*.json pelo campo "date".
Posts já publicados ficam em posts/publicados.json, para nunca publicar duas vezes.
"""
import argparse, datetime, glob, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = "https://raw.githubusercontent.com/gustavofillchar/byorbit-social-media/main/"
LOG = os.path.join(ROOT, "posts", "publicados.json")
API_VERSION = "v23.0"


def today():
    return datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()


def find_post(date):
    found = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "posts", "*.json"))):
        if f == LOG:
            continue
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for p in data if isinstance(data, list) else []:
            if isinstance(p, dict) and p.get("date") == date and p.get("slug"):
                found[p["slug"]] = p
    if len(found) > 1:
        sys.exit(f"Mais de um post com a data {date}: {sorted(found)}. Deixe só um.")
    return next(iter(found.values()), None)


def slides(slug):
    return sorted(glob.glob(os.path.join(ROOT, "posts", slug, f"{slug}-[0-9][0-9].png")))


def prepare(post):
    from PIL import Image
    out = []
    for png in slides(post["slug"]):
        jpg = png[:-4] + ".jpg"
        if not os.path.exists(jpg):
            Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True)
        out.append(jpg)
    if not out:
        sys.exit(f"Nenhuma arte encontrada em posts/{post['slug']}/")
    print(f"{len(out)} JPEGs prontos para {post['slug']}")


def api(method, path, **params):
    token = os.environ["IG_TOKEN"]
    host = "graph.instagram.com" if token.startswith("IG") else "graph.facebook.com"
    params["access_token"] = token
    url = f"https://{host}/{API_VERSION}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url + ("?" + data.decode() if method == "GET" else ""),
                                 data=None if method == "GET" else data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"Erro da API do Instagram em {path}: {body}")


def wait_ready(cid):
    for _ in range(30):
        st = api("GET", cid, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"Container {cid} com status {st}: {api('GET', cid, fields='status')}")
        time.sleep(10)
    sys.exit(f"Container {cid} não ficou pronto a tempo")


def publish(post, dry_run):
    log = json.load(open(LOG)) if os.path.exists(LOG) else {}
    if post["slug"] in log:
        print(f"{post['slug']} já foi publicado ({log[post['slug']]}). Nada a fazer.")
        return
    uid = os.environ["IG_USER_ID"]
    urls = [RAW + os.path.relpath(p[:-4] + ".jpg", ROOT) for p in slides(post["slug"])]
    if not 2 <= len(urls) <= 10:
        sys.exit(f"Carrossel precisa de 2 a 10 imagens; {post['slug']} tem {len(urls)}")
    children = []
    for u in urls:
        c = api("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
        children.append(c)
    for c in children:
        wait_ready(c)
    print(f"{len(children)} imagens aceitas pelo Instagram")
    carousel = api("POST", f"{uid}/media", media_type="CAROUSEL",
                   children=",".join(children), caption=post["caption"])["id"]
    wait_ready(carousel)
    if dry_run:
        print("Teste ok: carrossel montado e aceito, mas NÃO publicado (dry run).")
        return
    media_id = api("POST", f"{uid}/media_publish", creation_id=carousel)["id"]
    link = api("GET", media_id, fields="permalink").get("permalink", "")
    log[post["slug"]] = {"date": post["date"], "media_id": media_id, "permalink": link}
    json.dump(log, open(LOG, "w"), indent=1, ensure_ascii=False)
    print(f"Publicado: {link}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prepare", "publish"])
    ap.add_argument("--date", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--start", default=os.environ.get("START_DATE", ""))
    a = ap.parse_args()
    date = a.date or today()
    if a.start and date < a.start and not a.date:
        print(f"{date} ainda é coberto pelo Metricool (robô começa em {a.start}).")
        sys.exit(0)
    post = find_post(date)
    if not post:
        print(f"Nenhum post com data {date} em posts/*.json. Nada a publicar.")
        sys.exit(0)
    prepare(post) if a.step == "prepare" else publish(post, a.dry_run)
