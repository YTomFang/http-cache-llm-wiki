
from html import escape
from pathlib import Path
from check_content import ROOT, WIKI, WORKFLOW, load, read


CLAIM_LABELS = {
    "copy":"快取副本", "saving":"省下傳輸", "fresh":"新鮮度",
    "example":"60 秒示例", "reload":"重新整理", "validator":"驗證標記",
    "match":"304", "changed":"200 新版", "age":"max-age",
    "validate":"no-cache", "no-store":"no-store", "settings":"Network 設定",
    "inspect":"Headers"
}


def e(value):
    return escape(str(value), quote=True)


def write(path, content):
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def page(title, current, body, style, script=None):
    nav = []
    for key, label, path in [
        ("report", "成果總覽", "index.html"), ("wiki", "LLM Wiki", "wiki.html"),
        ("deck", "教學簡報", "slides.html")
    ]:
        attr = ' aria-current="page"' if current == key else ""
        nav.append(f'<a href="{path}"{attr}>{label}</a>')
    css = read(WORKFLOW / "base.css") + "\n" + read(WORKFLOW / style)
    js = f"<script>\n{read(WORKFLOW / script)}</script>" if script else ""
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<style>
{css}</style>
</head>
<body>
<header class="top"><div class="top-inner">
<a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">[HTTP]</span> 快取入門</a>
<nav class="nav" aria-label="成果導覽">{''.join(nav)}</nav>
</div></header>
{body}
{js}
</body>
</html>"""


def link_for_claim(ref):
    concept, claim = ref.split("/")
    return f'<a class="pill" href="wiki.html#{e(concept)}-{e(claim)}">{e(concept)} · {e(CLAIM_LABELS[claim])}</a>'


def cards(items, classes=""):
    return f'<div class="cards {classes}">' + "".join(
        f'<div class="card"><p class="label">{e(label)}</p><h3>{e(title)}</h3><p>{e(detail)}</p></div>'
        for label, title, detail in items
    ) + "</div>"


def steps(items):
    return '<ol class="steps">' + "".join(
        f'<li><div><strong>{e(title)}</strong><p>{e(detail)}</p></div></li>' for title, detail in items
    ) + "</ol>"


def quiz(items):
    blocks = []
    for item in items:
        choices = "".join(
            f'<button class="answer" type="button" data-correct="{str(n == item["answer"]).lower()}" aria-pressed="false">{e(label)}</button>'
            for n, label in enumerate(item["choices"])
        )
        blocks.append(f"""<div class="quiz" data-explanation="{e(item['explanation'])}">
<h3>{e(item['prompt'])}</h3>
<div class="answers">{choices}</div><p class="feedback" role="status"></p>
</div>""")
    return f'<div class="quiz-grid">{"".join(blocks)}</div>'


def render_slide(slide, index):
    sid = slide["id"]
    eyebrow = f'<p class="eyebrow">{e(slide["tag"])}</p>'
    lead = f'<p class="lead">{e(slide["lead"])}</p>'
    heading = f'<h2 id="{sid}-title">{e(slide["title"])}</h2>'
    if sid == "intro":
        rows = "".join(f'<div class="trace-row"><strong>{e(name)}</strong><span>{e(note)}</span></div>'
                       for name, note in slide["items"])
        content = f"""<div class="hero-grid"><div class="hero-copy">{eyebrow}
<h1 id="intro-title" aria-label="{e(slide['title'])}">HTTP 快取<br><strong>入門</strong></h1>{lead}</div>
<div class="trace"><p class="trace-label">GET /poster.png</p>{rows}</div></div>"""
    else:
        content = eyebrow + heading + lead
        if sid == "copy":
            content += cards(slide["items"]) + f'<p class="annotation">{e(slide["note"])}</p>'
        elif sid == "fresh":
            content += cards(slide["items"], "timeline")
        elif sid == "validate":
            content += f'<pre class="wire"><code>{e(slide["code"])}</code></pre>' + cards(slide["items"], "two")
        elif sid == "policy":
            content += '<div class="directives">' + "".join(
                f'<div class="directive"><code>{e(name)}</code><strong>{e(store)}</strong><span>{e(reuse)}</span></div>'
                for name, store, reuse in slide["items"]
            ) + "</div>"
        elif sid in {"lab", "takeaway"}:
            content += steps(slide["items"])
        elif sid == "quiz":
            content += quiz(slide["quizzes"])
    citations = "".join(map(link_for_claim, slide["citations"]))
    hidden = " hidden" if index else ""
    cover = " cover" if sid == "intro" else ""
    return f"""<section class="slide{cover}" id="{sid}" aria-labelledby="{sid}-title"{hidden}>
{content}
<footer class="citations"><span>Wiki 證據</span>{citations}</footer>
</section>"""


def render_deck(slides):
    options = "".join(f'<option value="{s["id"]}">{i + 1:02} · {e(s["title"])}</option>'
                      for i, s in enumerate(slides))
    sections = "\n".join(render_slide(s, i) for i,s in enumerate(slides))
    return page("HTTP 快取入門 · 教學簡報", "deck", f"""<main class="deck">
<noscript><style>.slide[hidden]{{display:flex!important;margin-top:12px}}.deck-controls,.progress{{display:none}}</style>
<p>可往下閱讀所有投影片。互動測驗需要 JavaScript。</p></noscript>
<div class="slides">{sections}</div>
<nav class="deck-controls" aria-label="投影片控制">
<button type="button" class="deck-button prev" id="previous" aria-keyshortcuts="ArrowLeft" disabled>← 上一頁</button>
<div class="page-control"><span id="page-count" role="status">01 / {len(slides):02}</span>
<select id="slide-select" class="jump" aria-label="跳至指定投影片">{options}</select></div>
<button type="button" class="deck-button next" id="next" aria-keyshortcuts="ArrowRight">下一頁 →</button>
</nav>
<div class="progress" aria-hidden="true"><div id="bar"></div></div>
</main>""", "deck.css", "deck.js")


def internal(href, label):
    return f'<a href="#{e(href)}">{e(label)}</a>'


def concept_card(k, source_by_id, concept_by_id):
    key = k["id"]
    claims = []
    for suffix, text, refs in k["claims"]:
        links = []
        for ref in refs:
            sid, section = ref.split("#")
            label = next(label for anchor,label,_ in source_by_id[sid]["refs"] if anchor == section)
            links.append(internal(f"{sid}-{section}", f"{sid} · {label}"))
        claims.append(f'<div class="claim" id="{key}-{e(suffix)}"><p>{e(text)}</p>'
                      f'<div>{"　".join(links)}</div></div>')
    related = "　".join(internal(r,concept_by_id[r]["title"]) for r in k["related"])
    return f"""<article class="wiki-card" id="{key}" data-tags="{e(k['tags'])}">
<h3><span class="key">{key}</span>{e(k['title'])}</h3><p>{e(k['question'])}</p>
{"".join(claims)}<p class="related">相關概念　{related}</p></article>"""


def source_card(source, concepts, received):
    sid = source["id"]
    sections = []
    for anchor, label, note in source["refs"]:
        sections.append(f"""<div class="source-section" id="{sid}-{e(anchor)}">
<h4>{e(label)}</h4><p>{e(note)}</p><a href="{e(source['url'])}#{e(anchor)}">查閱原文段落 ↗</a></div>""")
    related = "　".join(internal(k["id"], k["title"]) for k in concepts if any(
        ref.startswith(sid+"#") for _,_,refs in k["claims"] for ref in refs
    ))
    return f"""<article class="wiki-card" id="{sid}">
<h3><span class="key">{sid}</span>{e(source['title'])}</h3>
<p>{e(source['intro'])}</p><p class="origin">{e(source['by'])} · <time datetime="{e(received)}">{e(received[:16].replace('T',' '))}</time>（臺灣時間）擷取 ·
<a href="{e(source['url'])}">原文 ↗</a></p>
{"".join(sections)}<p class="related">相關概念　{related}</p></article>"""


def render_wiki(wiki, acquisitions):
    concepts, sources = [wiki[key] for key in ("concepts", "sources")]
    source_by_id = {s["id"]: s for s in sources}
    concept_by_id = {k["id"]: k for k in concepts}
    def index(entries):
        return "".join(
            f'<a href="#{a["id"]}"><span>{a["id"]}</span>{e(a["title"])}</a>' for a in entries
        )
    cards = "".join(concept_card(k, source_by_id, concept_by_id) for k in concepts)
    times = {record["source"]: record["received_taipei"] for record in acquisitions}
    sources_html = "".join(source_card(s, concepts, times[s["id"]]) for s in sources)
    return page("HTTP 快取入門 · LLM Wiki", "wiki", f"""<main class="reference">
<section class="mast"><div><div class="eyebrow">LLM WIKI</div><h1>瀏覽器 HTTP 快取</h1>
<p>查找副本如何儲存、何時過期、如何驗證，以及如何在 Chrome 觀察。每則說法都連回原文段落。</p></div>
<div class="pills"><span>{len(concepts)} 個概念條目</span><span>{len(sources)} 篇來源摘要</span></div></section>
<div class="split">
<aside class="side" aria-label="Wiki 索引">
<div class="search"><label for="wiki-search">搜尋 Wiki</label>
<input type="search" id="wiki-search" placeholder="如 ETag 或 304">
<output id="match-count" for="wiki-search" aria-live="polite"></output></div>
<h2>概念索引</h2><nav aria-label="概念索引">{index(concepts)}</nav>
<h2>來源索引</h2><nav aria-label="來源索引">{index(sources)}</nav>
</aside>
<div class="wiki-content">
<p id="no-result" hidden>找不到符合的條目。試試 304、max-age 或 DevTools。</p>
<h2>概念條目</h2>{cards}
<h2 class="source-group">來源摘要</h2>{sources_html}
</div></div>
</main>""", "reference.css", "wiki.js")


def main():
    slides = load(WORKFLOW / "draft-v1.json")
    wiki = load(WIKI / "knowledge.json")
    write(ROOT / "slides.html", render_deck(slides))
    acquisitions = load(WORKFLOW / "ingest.json")
    write(ROOT / "wiki.html", render_wiki(wiki, acquisitions))
    report = WORKFLOW / "report-body.html"
    if report.exists():
        report_body = read(report).replace("{{CAPTURE_TAIPEI}}", e(acquisitions[-1]["received_taipei"]))
        report_body = report_body.replace("{{CAPTURE_UTC}}", e(acquisitions[-1]["received_utc"]))
        write(ROOT / "index.html", page("HTTP 快取入門 · 作業成果", "report", report_body,
                                         "reference.css"))


if __name__ == "__main__":
    main()
