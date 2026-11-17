#!/usr/bin/env python3
"""Render README.md, data/papers.json and updates/DATE.md.
Usage: python3 build_readme.py SCORED_JSONL REPO_DIR [DATE]"""
import json, os, sys, datetime
from collections import defaultdict
ORDER = ["推理RL算法","RLHF/偏好对齐","奖励模型/PRM","Agent/工具RL","训练系统/效率","多模态RL","分析/实证","数据集/基准","技术报告"]
TIER = {"A": "推荐落地", "B": "方法新颖", "C": "参考"}

def link(p):
    t = p["title"].replace("|", "\\|")
    s = f"[{t}]({p['url']})"
    if p.get("arxiv") and "arxiv.org" not in p["url"]:
        s += f" [arXiv](https://arxiv.org/abs/{p['arxiv']})"
    return s

def venue(p):
    aw = (p.get("award") or "").lower()
    tag = " Oral" if "oral" in aw or "top-5" in aw else (" Spotlight" if "spotlight" in aw or "top-25" in aw else "")
    return f"{p['venue']} {p['year']}{tag}"

def main(scored, repo, date=None):
    date = date or datetime.date.today().isoformat()
    sc = {}
    for l in open(scored):
        p = json.loads(l); sc[p["id"]] = p
    revs = [json.loads(l) for l in open(os.path.join(repo, "data", "reviewed.jsonl"))]
    papers = []
    for r in revs:
        if r["tier"] == "X": continue
        p = dict(sc.get(r["id"], {"title": r["title"], "url": "", "venue": "?", "year": 0}))
        p["has_code"] = bool(p.get("code") or (p.get("signals") or {}).get("code"))
        p.pop("abstract", None); p.pop("signals", None)
        p.update(tier=r["tier"], category=r["category"], reason=r["reason"], reviewed_on=r["reviewed_on"])
        papers.append(p)
    papers.sort(key=lambda p: (p["tier"], -(p.get("citations") or 0)))
    json.dump(papers, open(os.path.join(repo, "data", "papers.json"), "w"), ensure_ascii=False, indent=1)

    by = defaultdict(list)
    for p in papers: by[p["category"]].append(p)
    nA = sum(p["tier"] == "A" for p in papers); nB = sum(p["tier"] == "B" for p in papers)
    nX = sum(r["tier"] == "X" for r in revs)
    L = ["# 大模型 + 强化学习论文精选（2023 至今）", "",
         f"> 最近更新：{date}　|　推荐落地 {nA} 篇 · 方法新颖 {nB} 篇 · 已审阅 {len(revs)} 篇（排除 {nX} 篇）", "",
         "来源：NeurIPS / ICML / ICLR / ACL / EMNLP / NAACL / AAAI / IJCAI 录用论文，以及高引用 arXiv 预印本。每周一自动增量更新。", "",
         "## 筛选标准", "",
         "1. **召回**：标题/摘要同时命中大模型与强化学习关键词（RLHF、RLVR、GRPO、DPO、奖励模型等）。",
         "2. **初筛打分**：开源代码、主流基准量化结果、效率/工程收益、Oral/Spotlight、引用增速（Semantic Scholar）为正向信号；立场/愿景类表述、缺少实验证据为负向信号；综述与 Position 论文直接排除。",
         "3. **人工审阅**：逐篇阅读摘要并分级——",
         "   - **A 推荐落地**：方法可复现、工程代价可控、已有开源实现或被工业界广泛采用；",
         "   - **B 方法新颖**：提出新的目标函数/算法/训练范式，具备实证支撑，但落地成熟度尚待验证；",
         "   - **C 参考**：技术报告、领域专用或分析性工作，作为背景参考；",
         "   - **X 排除**：与主题弱相关、缺乏实证或明显夸大，不进入列表。", "",
         "表中「引用」为 Semantic Scholar 引用数（更新日快照），「代码」指摘要或会议页面给出了开源链接。", "",
         "## 目录", ""]
    for c in ORDER:
        if by[c]: L.append(f"- [{c}](#{c.replace('/', '').lower()})（{len(by[c])}）")
    L.append("")
    for c in ORDER:
        if not by[c]: continue
        L += [f"## {c}", "", "| 评级 | 论文 | 会议/来源 | 引用 | 代码 | 要点 |", "|---|---|---|---|---|---|"]
        for p in by[c]:
            L.append(f"| {p['tier']} {TIER[p['tier']]} | {link(p)} | {venue(p)} | {p.get('citations') if p.get('citations') is not None else '-'} | "
                     f"{'✓' if p.get('has_code') else ''} | {p['reason']} |")
        L.append("")
    L += ["## 每周更新记录", ""]
    ud = os.path.join(repo, "updates")
    os.makedirs(ud, exist_ok=True)
    new = [p for p in papers if p["reviewed_on"] == date]
    U = [f"# {date} 更新", "", f"本次新增 {len(new)} 篇（A {sum(p['tier']=='A' for p in new)} / B {sum(p['tier']=='B' for p in new)} / C {sum(p['tier']=='C' for p in new)}）。", ""]
    for p in sorted(new, key=lambda p: (p["tier"], ORDER.index(p["category"]))):
        U.append(f"- **{p['tier']} · {p['category']}** {link(p)}（{venue(p)}）：{p['reason']}")
    open(os.path.join(ud, f"{date}.md"), "w").write("\n".join(U) + "\n")
    for f in sorted(os.listdir(ud), reverse=True)[:12]:
        L.append(f"- [{f[:-3]}](updates/{f})")
    L += ["", "## 目录结构", "", "- `data/papers.json`：入选论文（含元数据、评级与理由）",
          "- `data/reviewed.jsonl`：全部已审阅论文（含排除项），用于增量去重",
          "- `scripts/`：抓取、召回、打分、渲染脚本；流程见 `scripts/PIPELINE.md`", ""]
    open(os.path.join(repo, "README.md"), "w").write("\n".join(L))
    print(f"README: {len(papers)} papers; update file: {len(new)} new")
if __name__ == "__main__":
    main(*sys.argv[1:])
