
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

PACKAGE = Path(__file__).resolve().parents[1]
DATA = json.loads((PACKAGE / "wiki/knowledge.json").read_text(encoding="utf-8"))
TAIPEI = timezone(timedelta(hours=8))
LICENSES = {
    "S01": "https://www.rfc-editor.org/series/rfc-use/",
    "S02": "https://www.rfc-editor.org/series/rfc-use/",
    "S03": "https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Attrib_copyright_license",
    "S04": "https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Attrib_copyright_license",
    "S05": "https://developers.google.com/terms/site-policies",
}


def save(path, content):
    target = PACKAGE / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def section_link(ref):
    source, anchor = ref.split("#")
    return f"[{source}](../sources/{source}.md#{anchor})"


def capture(source, run):
    request = Request(source["url"], headers={"User-Agent": "HTTP-Cache-Wiki-Capture/1.0",
                                              "Accept": "text/html",
                                              "Accept-Encoding": "identity"})
    started = datetime.now(timezone.utc)
    with urlopen(request, timeout=30) as response:
        html = response.read()
        received = datetime.now(timezone.utc)
        assert response.status == 200 and response.headers.get_content_type() == "text/html"
        headers = {name.lower(): response.headers.get(name)
                   for name in ("Date", "Last-Modified", "ETag", "Content-Type",
                                "Content-Encoding", "Content-Length")
                   if response.headers.get(name) is not None}
        record = {
            "source": source["id"], "title": source["title"], "publisher": source["by"],
            "request_url": source["url"], "final_url": response.url, "status": response.status,
            "started_utc": started.isoformat(timespec="milliseconds"),
            "received_utc": received.isoformat(timespec="milliseconds"),
            "received_taipei": received.astimezone(TAIPEI).isoformat(timespec="milliseconds"),
            "response_headers": headers, "bytes": len(html),
            "sha256": hashlib.sha256(html).hexdigest(),
            "snapshot": f"raw/captures/{run}/{source['id']}.html.txt",
            "rights": LICENSES[source["id"]],
        }
    snapshot = PACKAGE / record["snapshot"]
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with snapshot.open("xb") as out:
        out.write(html)
    return html, record


def ingest():
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    summaries = {}
    acquisitions = []
    for source in DATA["sources"]:
        sid = source["id"]
        html, record = capture(source, run)
        soup = BeautifulSoup(html, "html.parser")
        for anchor, *_ in source["refs"]:
            assert soup.find(id=anchor), (sid, anchor)
        anchor, excerpt = source["excerpt"]
        text = " ".join(soup.get_text(" ", strip=True).split())
        assert excerpt in text, (sid, excerpt)
        record["sections"] = [key for key, *_ in source["refs"]]
        acquisitions.append(record)
        save(f"raw/{sid}.md", "\n".join([
            f"# {source['title']}", "", f"- 發布者：{source['by']}",
            f"- 原文：{source['url']}", f"- 最終 URL：{record['final_url']}",
            f"- 收到完整回應（臺灣時間）：{record['received_taipei']}",
            f"- 收到完整回應（UTC）：{record['received_utc']}",
            f"- HTTP：{record['status']} · {record['bytes']:,} 位元組",
            f"- 完整 HTML 擷取指紋（SHA-256）：{record['sha256']}",
            f"- [完整 HTML 快照]({record['snapshot'].removeprefix('raw/')})",
            f"- [來源授權與使用條款]({record['rights']})",
            f"- 原文節錄位置：{source['url']}#{anchor}", "",
            f"> {excerpt}", "", "快照以純文字檔名保存原始 HTML 位元組，可直接重算指紋。"
        ]))
        related = [k for k in DATA["concepts"] if any(
            r.startswith(sid+"#") for _,_,refs in k["claims"] for r in refs)]
        lines = [f"# {sid} · {source['title']}", "", source["intro"], "",
                 f"[擷取紀錄](../../raw/{sid}.md) · [原文]({source['url']})", ""]
        for key, label, note in source["refs"]:
            lines.extend([f'<a id="{key}"></a>', f"## {label}", "", note, "",
                          f"[查閱原文段落]({source['url']}#{key})", ""])
        lines.extend(["## 相關概念", ""] + [
            f"- [{k['id']} · {k['title']}](../concepts/{k['id']}.md)" for k in related])
        save(f"wiki/sources/{sid}.md", "\n".join(lines))
        summaries[sid] = related

    for k in DATA["concepts"]:
        lines = [f"# {k['id']} · {k['title']}", "", k["question"], "",
                 f"搜尋詞：{k['tags']}", ""]
        for claim, text, refs in k["claims"]:
            lines.extend([f'<a id="{claim}"></a>', f"## {k['id']}/{claim}", "", text, "",
                          "依據 " + "、".join(map(section_link, refs)), ""])
        lines.extend(["## 延伸閱讀", ""] + [f"- [{r}]({r}.md)" for r in k["related"]])
        save(f"wiki/concepts/{k['id']}.md", "\n".join(lines))

    index = ["# HTTP 快取入門 · LLM Wiki", "",
             "從圖片請求學會辨識直接重用、成功驗證與取得新版。", "", "## 概念索引", ""]
    index += [f"- [{k['id']} · {k['title']}](concepts/{k['id']}.md) ｜{k['question']} 搜尋詞：{k['tags']}"
              for k in DATA["concepts"]]
    index += ["", "## 來源索引", ""] + [
        f"- [{src['id']} · {src['title']}](sources/{src['id']}.md) ｜{src['intro']}" for src in DATA["sources"]]
    index += ["", "[Ingest／Query／Lint 日誌](log.md)"]
    save("wiki/index.md", "\n".join(index))
    save("wiki/log.md", "# Wiki 維護日誌\n\n"
         "本日誌記錄需求確認後的重跑。使用兩種時區記錄同一次取得回應的時間。\n\n" + "\n\n".join(
        f"## [{record['received_taipei']}] ingest | {src['id']} · {src['title']}\n\n"
        f"已取得 HTTP {record['status']}，核對 {len(src['refs'])} 個段落定位並更新來源摘要。"
        f"UTC 時間為 {record['received_utc']}，彙整概念證據時採用於 "
        + "、".join(k["id"] for k in summaries[src["id"]]) + "。"
        for src, record in zip(DATA["sources"], acquisitions)))
    save("workflow/ingest.json", json.dumps(acquisitions, ensure_ascii=False, indent=2))
    save("wiki/knowledge.json", json.dumps(DATA, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ingest()
    print(f"Ingest complete: {len(DATA['sources'])} sources, {len(DATA['concepts'])} concept articles, "
          f"{sum(len(k['claims']) for k in DATA['concepts'])} evidence claims")
