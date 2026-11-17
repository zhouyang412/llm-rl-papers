# 每周增量更新流程

本流程由 Claude 定时任务每周一执行；也可手动运行。所有脚本仅依赖 Python 3 标准库与 curl。

```bash
WORK=$(mktemp -d)            # 原始数据放在仓库之外
bash scripts/fetch.sh  $WORK/raw                 # 1. 抓取各会议录用列表（2023 至当年+1）
bash scripts/s2_pool.sh $WORK/raw/s2             # 2. Semantic Scholar 全量 LLM+RL 论文池（引用/摘要/arXiv ID）
python3 -I scripts/collect.py $WORK/raw $WORK/cands.jsonl          # 3. 关键词召回
python3 -I scripts/score.py   $WORK/cands.jsonl $WORK/raw/s2 $WORK/scored.jsonl   # 4. 合并引用 + 初筛打分（含高引 arXiv 预印本）
python3 -I scripts/select_new.py $WORK/scored.jsonl data/reviewed.jsonl $WORK/queue.txt 60   # 5. 生成待审队列
# 6. 人工（Claude）逐篇阅读 queue.txt，写出 judgments.tsv：id<TAB>A/B/C/X<TAB>类别<TAB>一句话理由
python3 -I scripts/add_reviews.py $WORK/scored.jsonl data/reviewed.jsonl $WORK/judgments.tsv
python3 -I scripts/build_readme.py $WORK/scored.jsonl .            # 7. 渲染 README / data/papers.json / updates/日期.md
```

## 分级标准

| 等级 | 含义 | 典型特征 |
|---|---|---|
| A 推荐落地 | 可直接用于生产或研发 | 开源实现、可复现的基准提升、工程代价可控、被主流框架或模型采用 |
| B 方法新颖 | 新目标函数/算法/范式 | 有实证支撑，但落地成熟度或通用性尚待验证 |
| C 参考 | 背景资料 | 技术报告、领域专用应用、分析或评测类工作 |
| X 排除 | 不收录 | 与 LLM+RL 弱相关（如扩散模型、纯 SFT）、无实验、立场/愿景类、明显夸大 |

类别取值：推理RL算法、RLHF/偏好对齐、奖励模型/PRM、Agent/工具RL、训练系统/效率、多模态RL、分析/实证、数据集/基准、技术报告。

## 增量规则

- `data/reviewed.jsonl` 记录所有已审阅论文（含排除项），已审阅的论文不会重复进入队列。
- 入队条件：初筛分 ≥ 5.5，或月均引用 ≥ 8，或近两年论文月均引用 ≥ 5。尚未入队的论文会随引用增长在后续周次自动入队。
- 新会议（如下一届 ICLR/ICML/NeurIPS、AAAI-27、EMNLP 等）在官网公布录用列表后由 `fetch.sh` 自动纳入。
- 引用数为当次运行的 Semantic Scholar 快照，`build_readme.py` 每周刷新。
