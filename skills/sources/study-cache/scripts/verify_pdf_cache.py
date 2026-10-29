"""Synthetic fixtures only. No network or model calls."""
import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from reportlab.pdfgen import canvas

spec = importlib.util.spec_from_file_location("cache", Path(__file__).with_name("study_cache.py"))
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)

def pdf(path, pages):
    c = canvas.Canvas(str(path))
    for lines in pages:
        y = 800
        for line in lines:
            c.drawString(40, y, line)
            y -= 14
        c.showPage()
    c.save()

def run():
    checks = []
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
        root = Path(tmp)
        path = root / "fixture.pdf"
        pages = [[f"Background page {n}: ordinary reference material."] * 30 for n in range(1, 21)]
        pages[6] = ["ALPHA policy budget: 1200 USD.", "ALPHA deadline: 2030-05-31.", "ALPHA exception: interns excluded."]
        pages[14] = ["BETA threshold: 45 percent.", "BETA unit: kilograms."]
        pages[19] = []
        pdf(path, pages)
        db = cache.connect(root / "cache.sqlite")
        args = NS(file=str(path), course="synthetic", remote_id="", revision="")
        first = cache.ingest(db, args)
        assert first["extracted_sections"] == 20
        checks.append("physical PDF page count preserved")
        second = cache.ingest(db, args)
        assert second["status"] == "unchanged" and second["extracted_sections"] == 0
        checks.append("unchanged extraction skipped")
        blank = cache.read(db, NS(source_id=first["source_id"], section=20, offset=0, max_chars=100))
        assert "OCR/visual review required" in blank["location"]
        checks.append("blank page marked unverified")
        full = "\n".join(text for _, text in cache.extract(path))
        cases = []
        for query, required in [
            ("ALPHA", ["1200 USD", "2030-05-31", "interns excluded"]),
            ("BETA", ["45 percent", "kilograms"]),
        ]:
            result = cache.search(db, NS(query=query, course="synthetic", limit=3, max_chars=1200))
            selected = "\n".join(h["text"] for h in result["hits"])
            assert all(fact in selected for fact in required)
            assert all("page " in h["location"] for h in result["hits"])
            payload = json.dumps(result, ensure_ascii=False)
            cases.append({"query": query, "full_text_chars": len(full),
                          "selected_text_chars": len(selected), "search_json_chars": len(payload),
                          "required_facts": len(required), "retained_facts": sum(f in selected for f in required),
                          "missing_required_facts": [f for f in required if f not in selected],
                          "retries_to_recover_required_facts": 0,
                          "page_locations": [h["location"] for h in result["hits"]]})
        checks.append("two queries retain all specified facts and page locations")
        tiny = cache.search(db, NS(query="ALPHA", course="synthetic", limit=1, max_chars=10))
        assert tiny["hits"][0]["truncated"]
        recovered = cache.read(db, NS(source_id=first["source_id"], section=7, offset=0, max_chars=1200))
        assert "interns excluded" in recovered["text"]
        checks.append("truncated excerpt requires expansion; full page recovers exception")
        assert not cache.search(db, NS(query="NOTFOUND", course="synthetic", limit=3, max_chars=100))["hits"]
        checks.append("no match remains no match")
        pdf(path, [["Changed document content."]])
        stale = cache.search(db, NS(query="ALPHA", course="synthetic", limit=3, max_chars=1200))
        assert not stale["hits"] and stale["skipped"]
        checks.append("changed PDF excluded until reingested")
        pdf(path, [[]])
        try:
            cache.ingest(db, args)
            raise AssertionError("blank PDF should fail")
        except ValueError as exc:
            assert "OCR" in str(exc)
        assert db.execute("SELECT count(*) FROM sections").fetchone()[0] == 20
        checks.append("all-blank extraction preserves previous cache without serving stale data")
        pdf(path, [["New content."]])
        assert cache.ingest(db, args)["extracted_sections"] == 1
        checks.append("changed readable PDF replaces prior sections")
        db.close()
    return {"checks_passed": checks, "cases": cases, "model_calls": 0,
            "actual_token_usage": None, "answer_quality_evaluated": False,
            "scope": "Synthetic English text PDF; no OCR, visual or model answer evaluation. Retry count is retrieval expansion only."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run()
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
