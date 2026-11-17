#!/bin/bash
# Page through Semantic Scholar bulk search for LLM+RL papers (all pages) into OUT_DIR/pool-*.json
OUT=${1:-.}; mkdir -p "$OUT"
Q='("reinforcement learning" | RLHF | RLAIF | RLVR | GRPO | PPO | DPO | "policy optimization" | "preference optimization" | "reward model" | "reward models" | "verifiable rewards") + ("language model" | "language models" | LLM | LLMs | "reasoning model")'
for y in 2023 2024 2025 2026 2027; do
  tok=""; n=0
  while :; do
    for i in $(seq 1 12); do
      args=(--data-urlencode "query=$Q" --data-urlencode 'fields=title,abstract,citationCount,venue,year,externalIds,publicationDate,authors' --data-urlencode "year=$y")
      [ -n "$tok" ] && args+=(--data-urlencode "token=$tok")
      code=$(curl -sS -m 120 -G "https://api.semanticscholar.org/graph/v1/paper/search/bulk" "${args[@]}" -o "$OUT/pool-$y-$n.json" -w "%{http_code}")
      [ "$code" = 200 ] && break; sleep $((5*i))
    done
    [ "$code" = 200 ] || { echo "FAIL $y page $n"; break; }
    tok=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1])).get('token') or '')" "$OUT/pool-$y-$n.json")
    n=$((n+1)); [ -z "$tok" ] && break; sleep 3
  done
  echo "$y pages=$n"
done
