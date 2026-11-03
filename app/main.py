"""FastAPI 应用入口：MovieLens 推荐系统 API。

启动方式：
    uvicorn app.main:app --host 0.0.0.0 --port 8000

接口文档（自动生成）：
    http://localhost:8000/docs
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse

from .models import get_engine
from .schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    EvaluateRequest,
    HealthResponse,
    MetricsResponse,
    MovieRecommendation,
    PredictRequest,
    PredictResponse,
)

app = FastAPI(
    title="MovieLens 推荐系统 API",
    description="基于 MovieLens 32M 的分布式增量电影推荐系统 · 服务化接口",
    version="1.0.0",
)


@app.get("/", include_in_schema=False)
async def root():
    """根路径重定向到交互式接口文档。"""
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def startup_event():
    """服务启动时预加载所有模型和数据。"""
    engine = get_engine()
    print(f"[startup] 模型加载完成，耗时 {engine.load_time}s，已加载: {engine.loaded_models}")


@app.get("/health", response_model=HealthResponse, summary="健康检查")
async def health():
    """返回服务状态、已加载模型与加载耗时。"""
    engine = get_engine()
    return HealthResponse(
        status="ok",
        modelsLoaded=engine.loaded_models,
        loadTimeSeconds=engine.load_time,
    )


@app.post("/predict", response_model=PredictResponse, summary="单用户推荐")
async def predict(req: PredictRequest):
    """为单个用户生成 Top-K 推荐。

    - **userId**: MovieLens 原始用户 ID（从 1 开始）
    - **topK**: 返回条数，默认 10，最大 100
    """
    engine = get_engine()
    try:
        result = engine.predict_single(req.userId, req.topK)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推理失败: {e}")

    recs = [MovieRecommendation(**r) for r in result["recommendations"]]
    return PredictResponse(
        userId=result["userId"],
        recommendations=recs,
        latencyMs=result["latencyMs"],
    )


@app.post("/predict/batch", response_model=BatchPredictResponse, summary="批量推荐")
async def predict_batch(req: BatchPredictRequest):
    """为多个用户批量生成 Top-K 推荐。

    - **userIds**: 用户 ID 列表，最多 200,000 个
    - **topK**: 每个用户返回条数，默认 10
    """
    engine = get_engine()
    try:
        result = engine.predict_batch(req.userIds, req.topK)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量推理失败: {e}")

    responses = []
    for r in result["results"]:
        recs = [MovieRecommendation(**rec) for rec in r["recommendations"]]
        responses.append(PredictResponse(
            userId=r["userId"],
            recommendations=recs,
            latencyMs=r["latencyMs"],
        ))

    return BatchPredictResponse(
        totalUsers=result["totalUsers"],
        results=responses,
        totalLatencyMs=result["totalLatencyMs"],
    )


@app.post("/predict/batch/csv", summary="批量推荐（CSV 流式输出）")
async def predict_batch_csv(req: BatchPredictRequest):
    """批量推荐的 CSV 流式版本，适合教师测试集大批量调用。

    输出格式：userId,rank,movieId,score（与 scripts/evaluate.py 约定一致）
    """
    engine = get_engine()

    def generate():
        yield "userId,rank,movieId,score\n"
        for uid in req.userIds:
            try:
                result = engine.predict_single(uid, req.topK)
                for rec in result["recommendations"]:
                    yield f"{uid},{rec['rank']},{rec['movieId']},{rec['score']:.6f}\n"
            except Exception:
                continue

    return StreamingResponse(generate(), media_type="text/csv")


@app.post("/evaluate", response_model=MetricsResponse, summary="在线评估")
async def evaluate(req: EvaluateRequest):
    """对预测结果 CSV 文件做 NDCG@10 / Recall@10 / MRR@10 评估。

    - **predFile**: 预测 CSV 路径（相对项目根或绝对路径）
    - **name**: 本次评估的标签名
    """
    engine = get_engine()
    t0 = time.perf_counter()
    try:
        result = engine.evaluate(req.predFile, req.name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {e}")

    result["latencyMs"] = round((time.perf_counter() - t0) * 1000, 2)
    return MetricsResponse(**result)


@app.get("/movies/{movie_id}", summary="查询电影信息")
async def get_movie(movie_id: int):
    """根据 movieId 查询电影名称和类型。"""
    engine = get_engine()
    info = engine.get_movie_info(movie_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"movieId {movie_id} 不存在")
    return info


@app.get("/sample/users", summary="获取样例用户")
async def sample_users(n: int = 10):
    """随机返回 n 个有候选集的用户 ID，方便前端测试。"""
    import numpy as np
    engine = get_engine()
    valid_users = np.flatnonzero(engine._cand.counts)
    if len(valid_users) == 0:
        return []
    rng = np.random.default_rng(42)
    sampled = rng.choice(valid_users, size=min(n, len(valid_users)), replace=False)
    # 转回原始 userId（code + 1）
    return [int(engine._cand.user_ids[u - 1]) for u in sampled]
