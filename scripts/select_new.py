#!/usr/bin/env python3
"""List not-yet-reviewed candidates worth a manual review this week.
Usage: python3 select_new.py SCORED_JSONL REVIEWED_JSONL OUT_TXT [MAX=60]
Rule: prescore >= 5.5, or citations/month >= 8, or (published this/last year and citations/month >= 5)."""
import json, sys, datetime
def main(scored, reviewed, out, mx=60):
    done = {json.loads(l)["id"] for l in open(reviewed)}
    yr = datetime.date.today().year
    q = []
    for l in open(scored):
        p = json.loads(l)
        if p["id"] in done: continue
        cpm = p.get("cites_per_month") or 0
        if p["prescore"] >= 5.5 or cpm >= 8 or (p["year"] >= yr - 1 and cpm >= 5):
            q.append(p)
    q.sort(key=lambda p: -(p["prescore"] + min(3, (p.get("cites_per_month") or 0) / 4)))
    q = q[:int(mx)]
    with open(out, "w") as f:
        for p in q:
            ab = (p["abstract"] or "(no abstract)").replace("\n", " ")
            f.write(f"ID={p['id']}\n{p['title']} | {p['venue']} {p['year']} {p.get('award') or ''} | "
                    f"cit={p.get('citations')} code={'Y' if p['signals']['code'] else 'N'} prescore={p['prescore']}\n{ab[:900]}\n\n")
    print(f"{len(q)} papers queued for review -> {out}")
if __name__ == "__main__":
    main(*sys.argv[1:])
