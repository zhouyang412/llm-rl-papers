#!/usr/bin/env python3
"""Recall LLM+RL candidate papers from top-venue proceedings.

Usage: python3 collect.py RAW_DIR OUT_JSONL
RAW_DIR layout (downloaded by fetch.sh):
  {iclr,icml,neurips}-YEAR.json   conference virtual-site data
  acl/{acl,emnlp,naacl}-YEAR.html ACL Anthology event pages
  aaai/AAAI-YY_*.html             AAAI OJS issue pages
  ijcai/YEAR.html                 IJCAI proceedings pages
"""
import glob, html, json, os, re, sys

LLM = re.compile(r"\b(LLMs?|large language models?|language models?|LMs?|VLMs?|MLLMs?|GPT-?\d|reasoning models?|"
                 r"chain[- ]of[- ]thought|instruction[- ]tun\w*|Qwen\w*|Llama\w*|DeepSeek\w*|transformer[- ]based agents?)\b", re.I)
RL_STRONG = re.compile(r"\b(reinforcement learning|RLHF|RLAIF|RLVR|RL\b|GRPO|PPO|DPO|policy optimi[sz]ation|"
                       r"preference optimi[sz]ation|reward model\w*|reward hacking|verifiable rewards?|policy gradient|"
                       r"process rewards?|outcome rewards?|PRMs?|actor[- ]critic|Q-learning|offline RL|online RL|self-play|"
                       r"advantage estimat\w*|KL[- ]regulari[sz]\w*|rejection sampling fine-tun\w*|on-policy|off-policy)\b", re.I)
LLM_RL_SPECIFIC = re.compile(r"\b(RLHF|RLAIF|RLVR|GRPO|DPO|preference optimi[sz]ation|verifiable rewards?|process rewards?|"
                             r"reward model\w*|reward hacking|agentic RL|R1-Zero|R1-style|o1-like)\b", re.I)
REASONING = re.compile(r"\b(reasoning|agents?|agentic|tool[- ]use|alignment)\b", re.I)
EXCLUDE_TITLE = re.compile(r"^\s*(position:|a survey|survey of|a review)|\bsurvey\b", re.I)

def norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())

def strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

def is_candidate(title, abstract):
    if EXCLUDE_TITLE.search(title):
        return False
    t_llm, t_rl = bool(LLM.search(title)), bool(RL_STRONG.search(title))
    a_llm = len(LLM.findall(abstract)); a_rl = len(RL_STRONG.findall(abstract))
    if t_rl and (t_llm or a_llm >= 1):
        return True
    if t_llm and a_rl >= 2:
        return True
    if not abstract:  # title-only sources
        return (t_rl and t_llm) or bool(LLM_RL_SPECIFIC.search(title)) or \
            (bool(re.search(r"reinforcement learning|\bRL\b|policy optimi", title, re.I)) and bool(REASONING.search(title)))
    return a_llm >= 2 and a_rl >= 3

def from_virtual(raw):
    for f in sorted(glob.glob(os.path.join(raw, "*-20*.json"))):
        conf, year = os.path.basename(f)[:-5].split("-")
        for r in json.load(open(f))["results"]:
            title = strip(r.get("name")); ab = strip(r.get("abstract"))
            dec = (r.get("decision") or r.get("eventtype") or "")
            code = r.get("url") if "github.com" in str(r.get("url")) else None
            if not code:
                m = re.search(r"https?://github\.com/[\w.\-]+/[\w.\-]+", ab)
                code = m.group(0).rstrip(".") if m else None
            link = r.get("paper_url") if r.get("paper_url") not in (None, "None") else \
                f"https://{conf}.cc{r.get('virtualsite_url','')}"
            authors = r.get("authors")
            if isinstance(authors, list):
                authors = ", ".join(a.get("fullname", "") for a in authors[:6])
            else:
                authors = ", ".join(re.findall(r"'fullname': '([^']+)'", str(authors))[:6])
            yield dict(title=title, abstract=ab, venue=conf.upper().replace("NEURIPS", "NeurIPS"),
                       year=int(year), award=dec, url=link, code=code, authors=authors)

ACL_RE = re.compile(r'<strong><a class=align-middle href=/(\d{4}\.[\w-]+\.\d+)/>(.*?)</a></strong><br>(.*?)</span></div>'
                    r'(?:<div class="card[^"]*" id=abstract-[^>]*><div class="card-body p-3 small">(.*?)</div>)?', re.S)
def from_acl(raw):
    for f in sorted(glob.glob(os.path.join(raw, "acl", "*.html"))):
        h = open(f).read()
        for pid, t, au, ab in ACL_RE.findall(h):
            vol = pid.split(".")[1]
            if not re.match(r"(acl|emnlp|naacl)-(long|short|main)$|findings-(acl|emnlp|naacl)$", vol):
                continue
            conf = re.search(r"(acl|emnlp|naacl)", vol).group(1).upper()
            yield dict(title=strip(t), abstract=strip(ab), venue=conf + (" Findings" if "findings" in vol else ""),
                       year=int(pid[:4]), award=vol, url=f"https://aclanthology.org/{pid}/", code=None,
                       authors=", ".join(strip(a) for a in re.findall(r"<a href=/people/[^>]*>(.*?)</a>", au)[:6]))

def from_aaai(raw):
    for f in sorted(glob.glob(os.path.join(raw, "aaai", "AAAI-*.html"))):
        year = 2000 + int(os.path.basename(f)[5:7]); h = open(f).read()
        for m in re.finditer(r'<h3 class="title">\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<div class="authors">(.*?)</div>', h, re.S):
            yield dict(title=strip(m.group(2)), abstract="", venue="AAAI", year=year, award="",
                       url=m.group(1), code=None, authors=re.sub(r"\s+", " ", strip(m.group(3))))

def from_ijcai(raw):
    for f in sorted(glob.glob(os.path.join(raw, "ijcai", "*.html"))):
        year = int(os.path.basename(f)[:4]); h = open(f).read()
        for m in re.finditer(r'<a class="title" href="(/proceedings/\d+/\d+)">(.*?)</a>\s*<div class="authors">(.*?)</div>', h, re.S):
            yield dict(title=strip(m.group(2)), abstract="", venue="IJCAI", year=year, award="",
                       url="https://ijcai.org" + m.group(1), code=None, authors=strip(m.group(3)))

def main(raw, out):
    seen, n_all, cands = {}, 0, []
    for src in (from_virtual, from_acl, from_aaai, from_ijcai):
        for p in src(raw):
            n_all += 1
            if not p["title"] or not is_candidate(p["title"], p["abstract"]):
                continue
            k = norm(p["title"])
            if k in seen:
                old = seen[k]
                if "oral" in p["award"].lower() or "spotlight" in p["award"].lower():
                    old["award"] = p["award"]
                old["code"] = old["code"] or p["code"]
                continue
            p["id"] = k[:80]; seen[k] = p; cands.append(p)
    with open(out, "w") as fo:
        for p in cands:
            fo.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"scanned {n_all} papers, {len(cands)} candidates -> {out}", file=sys.stderr)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
