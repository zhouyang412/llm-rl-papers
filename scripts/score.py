#!/usr/bin/env python3
"""Merge candidates with the Semantic Scholar pool, add arXiv preprints, compute a pre-score.
Usage: python3 score.py CANDS_JSONL S2_POOL_DIR OUT_JSONL [TODAY=YYYY-MM-DD]"""
import datetime, glob, json, math, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from collect import is_candidate, norm

BENCH = re.compile(r"\b(GSM8K|MATH(-500)?|AIME|AMC|Olympiad|HumanEval|MBPP|LiveCodeBench|Codeforces|SWE-bench|"
                   r"MMLU|GPQA|AlpacaEval|MT-Bench|Arena-Hard|HotpotQA|WebShop|ALFWorld|WebArena|BFCL|tau-bench|"
                   r"OSWorld|BrowseComp|GAIA|TruthfulQA|HH-RLHF|UltraFeedback|Minerva)\b", re.I)
NUM = re.compile(r"\d+(\.\d+)?\s?(%|x\b|×|points?|pp\b)", re.I)
CODE = re.compile(r"github\.com|code (is|are|will be) (publicly )?available|open[- ]source[ds]?|we release|publicly release|huggingface\.co", re.I)
EFF = re.compile(r"\b(efficien\w*|speed-?up|faster|reduc\w+ (the )?(cost|memory|compute|latency)|throughput|"
                 r"GPU hours|lightweight|plug-and-play|scalab\w+|stabl\w+)\b", re.I)
REAL = re.compile(r"\b(deploy\w*|production|industr\w+|real-world|online A/B|in the wild)\b", re.I)
HYPE = re.compile(r"\b(position paper|we argue|this position|we envision|vision paper|roadmap|manifesto|call to action|"
                  r"AGI|superintelligence|paradigm shift)\b", re.I)
VENUE_OK = re.compile(r"neural information|neurips|icml|international conference on machine learning|"
                      r"learning representations|iclr|association for computational linguistics|acl|emnlp|naacl|"
                      r"empirical methods|aaai|ijcai|colm|conference on language modeling", re.I)

def months(date, today):
    try: d = datetime.date.fromisoformat(date)
    except Exception: return 12
    return max(1.0, (today - d).days / 30.4)

def main(cin, pool_dir, out, today=None):
    today = datetime.date.fromisoformat(today) if today else datetime.date.today()
    pool = {}
    for f in glob.glob(os.path.join(pool_dir, "*.json")):
        for p in json.load(open(f)).get("data", []):
            if p.get("title"): pool[norm(p["title"])] = p
    cands = [json.loads(l) for l in open(cin)]
    ids = set()
    for c in cands:
        ids.add(c["id"])
        s = pool.get(norm(c["title"]))
        if s:
            c["citations"] = s.get("citationCount") or 0
            c["pub_date"] = s.get("publicationDate") or f"{s.get('year')}-06-01"
            c["arxiv"] = (s.get("externalIds") or {}).get("ArXiv")
            if not c["abstract"] and s.get("abstract"):
                c["abstract"] = s["abstract"]
        else:
            c["citations"] = None; c["pub_date"] = f"{c['year']}-06-01"
    # re-check relevance now that title-only entries may have abstracts
    cands = [c for c in cands if is_candidate(c["title"], c["abstract"])]
    # arXiv preprints not (yet) at a covered venue
    for k, s in pool.items():
        if k[:80] in ids or VENUE_OK.search(s.get("venue") or ""):
            continue
        ax = (s.get("externalIds") or {}).get("ArXiv")
        if not ax or not s.get("abstract") or not is_candidate(s["title"], s["abstract"]):
            continue
        m = months(s.get("publicationDate") or f"{s.get('year')}-06-01", today)
        cit = s.get("citationCount") or 0
        if cit / m < 4 and cit < 150:   # keep only clearly high-impact preprints
            continue
        v = s.get("venue") or ""
        v = "arXiv" if (not v or re.search(r"arxiv", v, re.I)) else v
        cands.append(dict(id=k[:80], title=s["title"], abstract=s["abstract"], venue=v,
                          year=int(s.get("year") or 0), award="", url=f"https://arxiv.org/abs/{ax}", code=None,
                          authors=", ".join(a.get("name", "") for a in (s.get("authors") or [])[:6]),
                          citations=cit, pub_date=s.get("publicationDate"), arxiv=ax))
    for c in cands:
        ab = c["abstract"] or ""; aw = (c.get("award") or "").lower()
        m = months(c.get("pub_date"), today); cit = c.get("citations") or 0
        c["cites_per_month"] = round(cit / m, 2)
        sig = dict(
            code=2 if (c.get("code") or CODE.search(ab)) else 0,
            bench=1 if BENCH.search(ab) else 0,
            numbers=1 if NUM.search(ab) else 0,
            efficiency=1 if EFF.search(ab) else 0,
            real_world=1 if REAL.search(ab) else 0,
            award=2 if "oral" in aw or "top-5" in aw else (1.5 if "spotlight" in aw or "top-25" in aw else 0),
            citations=round(min(5, math.log2(1 + c["cites_per_month"])), 2),
            hype=-3 if HYPE.search(ab + " " + c["title"]) else 0,
            no_evidence=-1 if ab and not (BENCH.search(ab) or NUM.search(ab)) else 0,
            findings=-0.5 if "Findings" in c["venue"] else 0,
            no_abstract=-1 if not ab else 0,
        )
        c["signals"] = sig; c["prescore"] = round(sum(sig.values()), 2)
    cands.sort(key=lambda c: -c["prescore"])
    with open(out, "w") as fo:
        for c in cands: fo.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(cands)} scored ({sum(1 for c in cands if c['url'].startswith('https://arxiv.org'))} preprints/other venues)", file=sys.stderr)

if __name__ == "__main__":
    main(*sys.argv[1:])
