
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflow"
WIKI = ROOT / "wiki"


def read(path):
    return path.read_text(encoding="utf-8")


def load(path):
    return json.loads(read(path))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query(outline):
    index = read(WIKI / "index.md")
    matches = re.findall(r"\[(K\d+) · [^\]]+\]\(concepts/([^)]+)\) ｜([^\n]+)", index)
    records = []
    for slide, question, terms, selected in outline:
        candidates = [
            key for key, filename, description in matches
            if any(term.casefold() in description.casefold() or
                   term.casefold() in read(WIKI / "concepts" / filename).casefold()
                   for term in terms)
        ]
        assert set(selected) <= set(candidates), (slide, candidates, selected)
        records.append({"slide": slide, "question": question, "terms": terms,
                        "candidates": candidates, "selected": selected})
    return records


def lint_wiki(wiki):
    source_refs = {
        f"{source['id']}#{section}"
        for source in wiki["sources"] for section, _, _ in source["refs"]
    }
    concepts = {concept["id"] for concept in wiki["concepts"]}
    referenced = set()
    evidence = {}
    for concept in wiki["concepts"]:
        assert set(concept["related"]) <= concepts - {concept["id"]}
        md = read(WIKI / "concepts" / f"{concept['id']}.md")
        for key, text, refs in concept["claims"]:
            assert refs and set(refs) <= source_refs
            assert text in md and f'id="{key}"' in md
            evidence[f"{concept['id']}/{key}"] = refs
            referenced.update(refs)
    for source in wiki["sources"]:
        md = read(WIKI / "sources" / f"{source['id']}.md")
        assert (ROOT / "raw" / f"{source['id']}.md").is_file()
        for section, _, _ in source["refs"]:
            assert f'id="{section}"' in md and f"{source['url']}#{section}" in md
    return evidence, len(referenced)


def check_draft(slides, queries, evidence):
    assert len(slides) == len(queries)
    assert [p["id"] for p in slides] == [q["slide"] for q in queries]
    covered_sources = set()
    citation_count = 0
    for slide, query_record in zip(slides, queries):
        refs = slide["citations"]
        assert refs and len(refs) == len(set(refs)), slide["id"]
        for ref in refs:
            assert ref in evidence and ref.split("/")[0] in query_record["selected"], (slide["id"], ref)
            covered_sources.update(r.split("#")[0] for r in evidence[ref])
        citation_count += len(refs)
    return sorted(covered_sources), citation_count


def check_conditions(slides):
    by_id = {slide["id"]: slide for slide in slides}
    fresh = by_id["fresh"]["items"][1][2]
    validate = by_id["validate"]["lead"]
    findings = []
    if "重新整理" in fresh or "正常再次請求" not in fresh:
        findings.append({
            "slide": "fresh", "page": 3, "text": fresh, "evidence": "K02/reload",
            "issue": "重新整理可能觸發驗證。直接重用的示例應限定為正常再次請求。"
        })
    if "ETag" not in validate or not ("若" in validate or "假設" in validate):
        findings.append({
            "slide": "validate", "page": 4, "text": validate, "evidence": "K03/validator",
            "issue": "此例應先交代快取副本附有 ETag，才有舊標記可帶入 If-None-Match。"
        })
    return findings


def main():
    wiki = load(WIKI / "knowledge.json")
    acquisitions = load(WORKFLOW / "ingest.json")
    assert {row["source"] for row in acquisitions} == {s["id"] for s in wiki["sources"]}
    for row in acquisitions:
        snapshot = (ROOT / row["snapshot"]).read_bytes()
        assert row["status"] == 200 and len(snapshot) == row["bytes"]
        assert hashlib.sha256(snapshot).hexdigest() == row["sha256"]
        taipei = datetime.fromisoformat(row["received_taipei"])
        utc = datetime.fromisoformat(row["received_utc"])
        assert taipei.utcoffset() == timedelta(hours=8) and taipei == utc
    print(f"Full-source snapshots: {len(acquisitions)} checksums and clock pairs verified")
    outline = load(WORKFLOW / "outline.json")
    evidence, linked_sections = lint_wiki(wiki)
    queries = query(outline)
    save(WORKFLOW / "query.json", queries)
    baseline = load(WORKFLOW / "draft-v0.json")
    first_sources, first_citations = check_draft(baseline, queries, evidence)
    assert len(first_sources) >= 5
    initial_findings = check_conditions(baseline)
    assert [entry["slide"] for entry in initial_findings] == ["fresh", "validate"]
    print(f"Baseline: {first_citations} valid page references; {len(initial_findings)} condition findings")

    evidence_gate = load(WORKFLOW / "evidence-gate.json")
    for gate in evidence_gate:
        concept, key = gate["evidence"].split("/")
        assert gate["evidence"] in evidence
        assert gate["wiki_term"] in read(WIKI / "concepts" / f"{concept}.md")
        candidate = next(record for record in queries if record["slide"] == gate["slide"])
        assert concept in candidate["selected"], candidate
    print(f"Outline gate: {len(evidence_gate)} request conditions confirmed from the Wiki")

    final_draft = load(WORKFLOW / "draft-v1.json")
    final_sources, citations = check_draft(final_draft, queries, evidence)
    findings = check_conditions(final_draft)
    changed = [after["id"] for before, after in zip(baseline, final_draft) if before != after]
    assert changed == [entry["slide"] for entry in initial_findings]
    assert len(final_sources) >= 5 and not findings
    repairs = [
        final_draft[2]["items"][1][2],
        final_draft[3]["lead"]
    ]
    save(WORKFLOW / "content-check.json", {
        "verified_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_count": len(wiki["sources"]), "concept_count": len(wiki["concepts"]),
        "evidence_count": len(evidence), "linked_sections": linked_sections,
        "slide_count": len(final_draft), "slide_citations": citations,
        "sources_used": final_sources, "outline_gate": evidence_gate,
        "v0_findings": [dict(finding, repair=repair) for finding, repair in zip(initial_findings, repairs)],
        "v1_findings": findings, "changed_slides": changed
    })
    print(f"Recheck: {len(final_draft)} slides, {citations} page references, "
          f"{len(final_sources)} sources covered, {len(findings)} condition findings")


if __name__ == "__main__":
    main()
