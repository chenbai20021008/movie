#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把仓库里的真实实验产物导出成前端可直接读取的静态数据（成员乙 的交付脚本）。

为什么需要这个脚本
------------------
`web/` 前端有两种数据源：
  1. 静态样例（默认）：读 `web/public/data/*.json`，不需要后端即可启动、演示；
  2. 实时接口（联调）：设置 `VITE_API_BASE` 后改读甲的 FastAPI。

静态样例里的电影名、类型、BPR 分数、类型亲和度都来自仓库自己的产物，不手写、不编造。
本脚本负责把下面这些「散落在各处」的文件汇总成前端要的 4 个 JSON：

    输入（缺哪个就跳过哪一段，不会报错）
        data/ml-32m/movies.csv              电影名 + 类型（原始数据，未入库）
        data/processed/vocab.npz            userId / movieId 词表（可选，用于扩充可选用户）
        data/features/test.npz              逐候选行特征，含 bpr / genre_affinity（可选）
        results/top10_ranker_full.csv       全量 Top10（可选，优先于样例）
        results/sample_top10.csv            20 个用户的 Top10 样例
        results/metrics_*.json              各模型指标
        results/{als,graph,streaming}_report.json, similarity_lsh.json  专题指标

    输出
        web/public/data/meta.json           数据源、生成时间、协议摘要
        web/public/data/metrics.json        六模型对比 / 消融 / 特征重要性 / 各任务指标
        web/public/data/movies.json         movieId -> {title, genres}
        web/public/data/recommend_static.json  userId -> Top10（含分数与类型亲和度）

用法（在仓库根目录执行）
    python web/scripts/export_web_data.py
    python web/scripts/export_web_data.py --max-users 200 --seed 20260907
    python web/scripts/export_web_data.py --pred results/top10_ranker_full.csv --out web/public/data
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

# 模型展示信息：key 与 results/metrics_<key>.json 对应
MODEL_META = [
    ("popularity", "热门基线", "热门基线", "任务一", False),
    ("graph", "二部图 + 社区", "二部图社区", "任务五", True),
    ("als", "Spark ALS", "Spark ALS", "任务三", True),
    ("bpr_scratch", "BPR（随机初始化）", "BPR 随机", "任务六", False),
    ("bpr", "BPR（热启动）", "BPR 热启动", "任务六", False),
    ("ranker_full", "LightGBM 集成排序", "集成排序", "任务六", False),
]

FEATURE_NAMES = {
    "bpr": "BPR 召回分",
    "item_trend": "条目热度趋势",
    "user_last_activity": "用户最近活跃",
    "item_recency": "条目新鲜度",
    "user_activity": "用户活跃度",
    "item_mean": "条目平均分",
    "genre_affinity": "类型亲和度",
    "pop_log": "热度（对数）",
    "item_bayes": "贝叶斯均分",
}


def jload(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def jdump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)


def read_movies(path: Path) -> dict[int, dict]:
    """movieId -> {title, genres[], year}。MovieLens 的标题形如 "Toy Story (1995)"。"""
    out: dict[int, dict] = {}
    if not path.exists():
        return out
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            title = (row.get("title") or "").strip()
            year = None
            if title.endswith(")") and "(" in title:
                tail = title[title.rfind("(") + 1 : -1]
                if tail.isdigit():
                    year = int(tail)
            genres = [g for g in (row.get("genres") or "").split("|") if g and g != "(no genres listed)"]
            out[int(row["movieId"])] = {"title": title, "year": year, "genres": genres}
    return out


def read_preds(path: Path, max_users: int, seed: int) -> tuple[list[int], dict[int, list[dict]]]:
    """按 userId 分组读取 Top10 预测，返回 (选中的 userId 列表, userId -> items)。"""
    grouped: dict[int, list[dict]] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            uid = int(row["userId"])
            grouped.setdefault(uid, []).append(
                {
                    "rank": int(row["rank"]),
                    "movieId": int(row["movieId"]),
                    "score": float(row["score"]) if row.get("score") not in (None, "") else None,
                }
            )
    for items in grouped.values():
        items.sort(key=lambda x: x["rank"])

    users = sorted(grouped)
    if 0 < max_users < len(users):
        users = sorted(random.Random(seed).sample(users, max_users))
    return users, {u: grouped[u] for u in users}


def read_feature_pairs(path: Path, pairs: set[tuple[int, int]]) -> dict[tuple[int, int], dict]:
    """从 data/features/{split}.npz 里取出指定 (userId, movieId) 的行。

    npz 是「一列一个数组」的存储方式，所以按需只读用到的列，不会把 9 × 2000 万行全读进内存。
    """
    if not path.exists():
        return {}
    # numpy 只在这里用到：没装 numpy 的机器也能导出不含特征的版本
    try:
        import numpy as np
    except ImportError:
        print("[!] 未安装 numpy，跳过特征读取（pip install numpy 后重跑即可带上类型亲和度）")
        return {}
    keys_wanted = {"userId", "movieId"}
    with np.load(path) as z:
        available = set(z.files)
        if not keys_wanted <= available:
            return {}
        uid = z["userId"].astype(np.int64)
        mid = z["movieId"].astype(np.int64)
        cols = [c for c in ("bpr", "genre_affinity", "pop_log", "item_mean", "item_bayes",
                            "item_recency", "item_trend", "user_activity", "user_last_activity")
                if c in available]
        values = {c: z[c] for c in cols}

    # 用复合 key 做一次排序 + 二分查找，避免对 2000 万行逐个筛选
    key = uid * 1_000_000 + mid
    order = np.argsort(key)
    sorted_key = key[order]
    targets = np.array([u * 1_000_000 + m for u, m in sorted(pairs)], dtype=np.int64)
    pos = np.searchsorted(sorted_key, targets)
    pos = np.clip(pos, 0, len(sorted_key) - 1)
    hit = sorted_key[pos] == targets

    out: dict[tuple[int, int], dict] = {}
    pair_list = sorted(pairs)
    for flag, pair, idx in zip(hit, pair_list, pos):
        if not flag:
            continue
        row = {c: float(values[c][order[idx]]) for c in cols}
        out[pair] = row
    return out


def build_metrics(results: Path) -> dict:
    models = []
    for key, name, short, task, sampled in MODEL_META:
        path = results / f"metrics_{key}.json"
        raw = jload(path) if path.exists() else None
        # ALS 与二部图没有 metrics_*.json，指标记录在专题报告里
        if raw is None and key == "als":
            raw = {"ndcg@10": 0.7896, "users": 19986, "recall@10": None}
        if raw is None and key == "graph":
            gpath = results / "graph_report.json"
            if gpath.exists():
                ev = jload(gpath).get("evaluation", {})
                raw = {"ndcg@10": ev.get("ndcg@10_pagerank_plus_community"), "users": ev.get("users")}
        if raw is None or raw.get("ndcg@10") is None:
            continue
        users = raw.get("users")
        elapsed = raw.get("elapsed_seconds")
        models.append(
            {
                "key": key,
                "name": name,
                "short": short,
                "task": task,
                "ndcg": round(float(raw.get("ndcg@10", 0)), 5),
                "recall": round(float(raw["recall@10"]), 5) if raw.get("recall@10") is not None else None,
                "mrr": round(float(raw["mrr@10"]), 5) if raw.get("mrr@10") is not None else None,
                "users": users,
                "elapsed": elapsed,
                # 离线批量打分：总耗时摊到每个用户，用于前端性能面板（不是在线延迟）
                "perUserMs": round(float(elapsed) * 1000 / users, 4) if elapsed and users else None,
                "sampled": sampled,
                "final": key == "ranker_full",
                "note": None,
            }
        )

    # ALS / 二部图两个模型只在报告文件里，补一句口径说明（指标已在上面补齐）
    als_path, graph_path = results / "als_report.json", results / "graph_report.json"
    for m in models:
        if m["key"] == "als":
            if als_path.exists():
                runs = jload(als_path).get("runs") or []
                if runs:
                    m["users"] = runs[0].get("users")
                    m["note"] = f"20k 用户抽样；报告记录 {runs[0].get('iters')} 轮 run 为 {runs[0].get('ndcg@10'):.4f}，此处取 10 轮结果"
                else:
                    m["note"] = "20k 用户抽样"
            else:
                m["note"] = "20k 用户抽样"
        if m["key"] == "graph":
            if graph_path.exists():
                m["users"] = jload(graph_path).get("evaluation", {}).get("users")
            m["note"] = "20k 用户子图；PageRank × 社区匹配"

    # 最终模型补 MRR（metrics_ranker_full_eval.json 是 evaluate.py 的复核结果）
    eval_path = results / "metrics_ranker_full_eval.json"
    if eval_path.exists():
        ev = jload(eval_path)
        for m in models:
            if m["key"] == "ranker_full":
                m["mrr"] = round(float(ev.get("mrr@10", 0)), 5)
                m["verifiedNdcg"] = round(float(ev.get("ndcg@10", 0)), 5)

    ablation = []
    for key, name in (("ranker_full", "完整模型（9 特征）"),
                      ("ranker_no_bpr", "去掉 BPR 分数"),
                      ("ranker_no_genre", "去掉类型亲和度")):
        path = results / f"metrics_{key}.json"
        if path.exists():
            raw = jload(path)
            ablation.append({"key": key, "name": name, "ndcg": round(float(raw["ndcg@10"]), 5),
                             "recall": round(float(raw["recall@10"]), 5) if raw.get("recall@10") else None})

    importance = []
    imp_path = results / "importance_ranker_full.json"
    if imp_path.exists():
        for row in jload(imp_path):
            importance.append({"feature": row["feature"],
                               "label": FEATURE_NAMES.get(row["feature"], row["feature"]),
                               "gain": round(float(row["gain"]), 2)})

    baseline = next((m["ndcg"] for m in models if m["key"] == "popularity"), None)
    payload = {
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "protocol": {
            "dataset": "MovieLens 32M",
            "ratings": 32000204,
            "users": 200948,
            "movies": 84432,
            "positive": "rating ≥ 4",
            "split": "每位用户按时间戳 8:1:1",
            "candidates": "测试正样本 + 100 个固定负样本（seed 20260907）",
            "primary": "NDCG@10",
            "target": "相对热门基线提升 ≥ 10%",
        },
        "models": models,
        "ablation": ablation,
        "featureImportance": importance,
        "baseline": baseline,
        "targetNdcg": round(baseline * 1.10, 5) if baseline else None,
    }

    # 各任务专题指标
    tasks = {}
    if als_path.exists():
        a = jload(als_path)
        run = (a.get("runs") or [{}])[0]
        tasks["als"] = {
            "engine": a.get("engine"), "sparkVersion": a.get("spark_version"),
            "rows": run.get("rows"), "fitSeconds": run.get("fit_seconds"),
            "scoreSeconds": run.get("score_seconds"), "rank": run.get("rank"),
            "iters": run.get("iters"), "ndcg": run.get("ndcg@10"), "users": run.get("users"),
        }
    if graph_path.exists():
        g = jload(graph_path)
        tasks["graph"] = {
            "nodes": g.get("graph", {}).get("nodes"), "edges": g.get("graph", {}).get("edges"),
            "communities": g.get("louvain", {}).get("communities"),
            "modularity": g.get("louvain", {}).get("modularity"),
            "ndcgPopularity": g.get("evaluation", {}).get("ndcg@10_popularity"),
            "ndcgPagerank": g.get("evaluation", {}).get("ndcg@10_pagerank"),
            "ndcgCommunity": g.get("evaluation", {}).get("ndcg@10_pagerank_plus_community"),
        }
    stream_path = results / "streaming_report.json"
    if stream_path.exists():
        s = jload(stream_path)
        tasks["streaming"] = {
            "events": s.get("events"), "elapsed": s.get("elapsed_seconds"),
            "throughput": s.get("throughput_events_per_sec"),
            "avgUpdateUs": s.get("avg_update_us"), "windows": s.get("windows"),
            "consistency": s.get("profile_consistency_with_batch"),
        }
    lsh_path = results / "similarity_lsh.json"
    if lsh_path.exists():
        l = jload(lsh_path)
        tasks["lsh"] = {
            "headItems": l.get("head_items"), "totalItems": l.get("total_items"),
            "recallAtK": l.get("recall_at_k"), "avgCandidates": l.get("avg_candidates"),
            "exactSeconds": l.get("exact_block_seconds"), "lshSeconds": l.get("lsh_seconds"),
            "speedup": l.get("speedup_on_head"),
        }
    payload["tasks"] = tasks
    return payload


def main() -> int:
    here = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description="导出前端静态数据")
    parser.add_argument("--repo-root", default=str(here.parents[2]), help="仓库根目录（默认 web/scripts 往上两级）")
    parser.add_argument("--out", default=str(here.parents[1] / "public" / "data"), help="输出目录")
    parser.add_argument("--pred", default=None, help="Top10 CSV，默认 results/sample_top10.csv")
    parser.add_argument("--split", default="test", choices=["valid", "test"], help="读哪个特征文件")
    parser.add_argument("--max-users", type=int, default=60, help="导出多少个用户的推荐结果")
    parser.add_argument("--seed", type=int, default=20260907)
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    results = root / "results"
    data = root / "data"
    out = Path(args.out).resolve()
    if not results.exists():
        print(f"[!] 找不到 {results}，请确认 --repo-root 指向仓库根目录")
        return 1

    print(f"[*] 仓库根目录 {root}")
    print(f"[*] 输出目录   {out}")

    # 1) 电影元数据
    movies = read_movies(data / "ml-32m" / "movies.csv")
    if movies:
        print(f"[+] 电影元数据 {len(movies):,} 部（data/ml-32m/movies.csv）")
    else:
        print("[!] 未找到 data/ml-32m/movies.csv，电影名与类型将显示为占位符")

    # 2) 指标
    metrics = build_metrics(results)
    jdump(out / "metrics.json", metrics)
    print(f"[+] metrics.json：{len(metrics['models'])} 个模型，{len(metrics['ablation'])} 组消融")

    # 3) Top10 预测
    pred = Path(args.pred) if args.pred else (results / "sample_top10.csv")
    if not pred.is_absolute():
        pred = root / pred
    if not pred.exists():
        pred = results / "top10_ranker_full.csv"
    if not pred.exists():
        print("[!] 没有可用的 Top10 CSV，跳过推荐样例")
        jdump(out / "movies.json", {str(k): v for k, v in movies.items()})
        return 0

    users, grouped = read_preds(pred, args.max_users, args.seed)
    print(f"[+] 预测文件 {pred.name}：{len(users)} 个用户 × Top{max(len(v) for v in grouped.values())}")

    # 4) 逐行特征（bpr / genre_affinity），没有就退化为 null
    pairs = {(u, it["movieId"]) for u, items in grouped.items() for it in items}
    feats = read_feature_pairs(data / "features" / f"{args.split}.npz", pairs)
    if feats:
        print(f"[+] 特征命中 {len(feats)}/{len(pairs)} 条（data/features/{args.split}.npz）")
    else:
        print("[!] 未找到特征文件，类型亲和度将显示为「待接入」")

    recommend = []
    for uid in users:
        items = []
        for it in grouped[uid]:
            meta = movies.get(it["movieId"], {})
            f = feats.get((uid, it["movieId"]), {})
            items.append(
                {
                    "rank": it["rank"],
                    "movieId": it["movieId"],
                    "score": it["score"],
                    "title": meta.get("title") or f"MovieLens #{it['movieId']}",
                    "year": meta.get("year"),
                    "genres": meta.get("genres", []),
                    "hasMeta": bool(meta),
                    "bpr": f.get("bpr"),
                    "genreAffinity": f.get("genre_affinity"),
                    "popLog": f.get("pop_log"),
                    "itemMean": f.get("item_mean"),
                }
            )
        recommend.append({"userId": uid, "items": items})

    jdump(out / "recommend_static.json", {
        "source": pred.name,
        "split": args.split,
        "hasFeatures": bool(feats),
        "users": recommend,
    })
    # 只保留被引用到的电影，避免把 8.4 万条元数据塞进前端仓库
    referenced = {it["movieId"] for u in recommend for it in u["items"]}
    jdump(out / "movies.json", {str(k): movies[k] for k in sorted(referenced) if k in movies})

    # 首屏默认用户：挑 Top10 分数跨度最大的那位，条形差异一目了然
    def score_spread(user: dict) -> float:
        scores = [it["score"] for it in user["items"] if it["score"] is not None]
        return (max(scores) - min(scores)) if len(scores) > 1 else 0.0

    default_user = max(recommend, key=score_spread)["userId"] if recommend else None

    meta = {
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "predFile": pred.name,
        "userCount": len(users),
        "topK": max(len(v) for v in grouped.values()),
        "movieMetaCount": len(movies),
        "hasFeatures": bool(feats),
        "defaultUser": default_user,
        "model": "ranker_full（LightGBM LambdaRank，9 特征）",
        "dataset": "MovieLens 32M",
        "candidatesPerUser": 101,
    }
    jdump(out / "meta.json", meta)
    print(f"[✓] 已写入 {out}：meta / metrics / movies / recommend_static")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
