# byorbit-social-media

Artes dos carrosséis do Instagram da ByOrbit (@byorbit.tech).
As imagens em `posts/` são públicas de propósito: o Metricool publica a partir destes links.

- `kit/template.html`: template visual (Geist, paleta do site, órbita)
- `kit/render_posts.py`: `python3 -I kit/render_posts.py kit posts.json saida/`
- Fontes Geist (SIL OFL 1.1): baixar de github.com/vercel/geist-font para `kit/fonts/` antes de renderizar

## Anúncios (sob demanda, fora do robô de publicação)

Nada em `anuncios/` é publicado automaticamente: o robô só lê `posts/`.

- `kit/ads.html`: template de criativos. Tipos: `scene` (foto + cards flutuantes com fluxo), `chat` (conversa no celular), `split` (antes/depois), `statement` (oferta com preço)
- Formatos: `feed` 1080x1350 (4:5) e `story` 1080x1920 (9:16, respeitando as zonas seguras). Faça sempre os dois.
- Render: `python3 -I kit/render_ads.py kit anuncios/<campanha>.json anuncios/`
- Fotos: edite `anuncios/fotos.json` (`{"nome": {"query": "...", "orientation": "portrait", "n": 4}}`) e dê push; a Action `fotos-anuncios.yml` busca no Unsplash e salva em `anuncios/img/<nome>-N.jpg`, com créditos em `anuncios/img/creditos.json`
