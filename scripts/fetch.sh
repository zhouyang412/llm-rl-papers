#!/bin/bash
# Download raw proceedings data into RAW_DIR (default ./raw). Years: 2023 .. current year + 1.
set -u
RAW=${1:-raw}; mkdir -p "$RAW"/{acl,aaai,ijcai}
Y1=2023; Y2=$(( $(date +%Y) + 1 ))
get(){ code=$(curl -sS -m 180 -L -o "$1" -w "%{http_code}" "$2"); [ "$code" = 200 ] || rm -f "$1"; }
for y in $(seq $Y1 $Y2); do
  for c in iclr icml neurips; do get "$RAW/$c-$y.json" "https://$c.cc/static/virtual/data/$c-$y-orals-posters.json" & done
  for e in acl emnlp naacl; do get "$RAW/acl/$e-$y.html" "https://aclanthology.org/events/$e-$y/" & done
  get "$RAW/ijcai/$y.html" "https://ijcai.org/proceedings/$y/" &
  wait
done
# drop virtual-site files that are not valid paper lists (e.g. future years not yet published)
for f in "$RAW"/*-20*.json; do python3 -I -c "import json,sys;d=json.load(open(sys.argv[1]));assert d['results']" "$f" 2>/dev/null || rm -f "$f"; done
for f in "$RAW"/acl/*.html "$RAW"/ijcai/*.html; do [ -s "$f" ] && grep -qE 'align-middle href=/|class="title" href="/proceedings' "$f" || rm -f "$f"; done
# AAAI: technical tracks + alignment/safety special tracks
for p in 1 2 3 4 5 6; do get "$RAW/aaai/archive$p.html" "https://ojs.aaai.org/index.php/AAAI/issue/archive/$p"; done
cat "$RAW"/aaai/archive*.html | python3 -I -c "
import re,sys
h=sys.stdin.read(); seen=set()
for m in re.finditer(r'<a class=\"title\" href=\"https://ojs.aaai.org/index.php/AAAI/issue/view/(\d+)\">\s*(.*?)\s*</a>',h,re.S):
    t=re.sub(r'\s+',' ',m.group(2))
    if re.match(r'AAAI-(2[3-9]|[3-9]\d) (Technical Tracks|Special Track on AI Alignment|Special Track Safe|Special Tracks$)',t) and m.group(1) not in seen:
        seen.add(m.group(1)); print(m.group(1), re.sub(r'[^A-Za-z0-9-]+','_',t))
" > "$RAW/aaai/issues.txt"
while read id name; do [ -s "$RAW/aaai/$name.html" ] || get "$RAW/aaai/$name.html" "https://ojs.aaai.org/index.php/AAAI/issue/view/$id"; done < "$RAW/aaai/issues.txt"
ls "$RAW"/*.json "$RAW"/acl "$RAW"/aaai "$RAW"/ijcai | wc -l
