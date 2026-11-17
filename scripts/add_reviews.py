#!/usr/bin/env python3
"""Append manual judgments to reviewed.jsonl.
Usage: python3 add_reviews.py SCORED_JSONL REVIEWED_JSONL JUDGMENTS_TSV [DATE]
JUDGMENTS_TSV columns: id<TAB>tier(A/B/C/X)<TAB>category<TAB>one-line reason (Chinese)"""
import json, sys, datetime
CATS = {"推理RL算法","RLHF/偏好对齐","奖励模型/PRM","Agent/工具RL","训练系统/效率","多模态RL","分析/实证","数据集/基准","技术报告"}
def main(scored, reviewed, tsv, date=None):
    date = date or datetime.date.today().isoformat()
    sc = {json.loads(l)["id"]: json.loads(l) for l in open(scored)}
    done = {json.loads(l)["id"] for l in open(reviewed)}
    n = 0
    with open(reviewed, "a") as fo:
        for line in open(tsv):
            if not line.strip(): continue
            pid, tier, cat, reason = line.rstrip("\n").split("\t")
            assert tier in "ABCX" and cat in CATS, line
            if pid in done or pid not in sc: continue
            fo.write(json.dumps(dict(id=pid, title=sc[pid]["title"], tier=tier, category=cat, reason=reason,
                                     reviewed_on=date), ensure_ascii=False) + "\n"); n += 1
    print(f"added {n} reviews")
if __name__ == "__main__":
    main(*sys.argv[1:])
