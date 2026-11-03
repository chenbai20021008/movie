"""Pydantic 数据模型：定义 API 的输入输出格式。"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------- 请求模型 ----------

class PredictRequest(BaseModel):
    """单用户推荐请求。"""
    userId: int = Field(..., description="用户 ID（MovieLens 原始 userId）")
    topK: int = Field(10, ge=1, le=100, description="返回 Top-K 条推荐，默认 10")


class BatchPredictRequest(BaseModel):
    """批量推荐请求。"""
    userIds: list[int] = Field(..., min_length=1, max_length=200000, description="用户 ID 列表")
    topK: int = Field(10, ge=1, le=100, description="每个用户返回 Top-K 条")


class EvaluateRequest(BaseModel):
    """在线评估请求：传入预测 CSV 路径，返回指标。"""
    predFile: str = Field(..., description="预测结果 CSV 文件路径（相对项目根或绝对路径）")
    name: str = Field("api_eval", description="本次评估的模型名称标签")


# ---------- 响应模型 ----------

class MovieRecommendation(BaseModel):
    """单条电影推荐。"""
    rank: int = Field(..., description="排名，从 1 开始")
    movieId: int = Field(..., description="电影 ID（MovieLens 原始 movieId）")
    score: float = Field(..., description="模型打分")


class PredictResponse(BaseModel):
    """单用户推荐响应。"""
    userId: int
    recommendations: list[MovieRecommendation]
    latencyMs: float = Field(..., description="推理耗时（毫秒）")


class BatchPredictResponse(BaseModel):
    """批量推荐响应。"""
    totalUsers: int
    results: list[PredictResponse]
    totalLatencyMs: float = Field(..., description="整批推理总耗时（毫秒）")


class MetricsResponse(BaseModel):
    """评估指标响应。"""
    model: str
    ndcg10: float
    recall10: float
    mrr10: float | None = None
    users: int
    latencyMs: float


class HealthResponse(BaseModel):
    """健康检查响应。"""
    status: str
    modelsLoaded: list[str]
    loadTimeSeconds: float
    version: str = "1.0.0"
