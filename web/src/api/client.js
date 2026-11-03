/**
 * 数据源客户端：一套接口，两种后端
 *
 *   static（默认）读 web/public/data/*.json —— 甲的接口没就绪时也能独立开发、独立演示
 *   api           走 /api 反向代理到甲的 FastAPI —— 联调时只改一个环境变量
 *
 * 切换方式：.env.local 里设置 VITE_DATA_SOURCE=api，重启 npm run dev。
 * 页面不需要改任何一行代码，这正是分工文档里「④ 静态开发 → ⑥ 切换真实接口」的落地方式。
 */

const MODE = (import.meta.env.VITE_DATA_SOURCE || 'static').toLowerCase() === 'api' ? 'api' : 'static'
const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const STATIC_BASE = `${import.meta.env.BASE_URL}data`
const REQUEST_TIMEOUT = 5000

export const dataSource = MODE

/* ------------------------------------------------------------------ */
/* 基础请求                                                            */
/* ------------------------------------------------------------------ */

async function request(url, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), options.timeout || REQUEST_TIMEOUT)
  const started = performance.now()
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...(options.headers || {}) },
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`${res.status} ${res.statusText}${text ? ` · ${text.slice(0, 120)}` : ''}`)
    }
    const data = await res.json()
    return { data, latencyMs: performance.now() - started }
  } finally {
    clearTimeout(timer)
  }
}

const staticCache = new Map()

function loadStatic(name) {
  if (!staticCache.has(name)) {
    staticCache.set(
      name,
      request(`${STATIC_BASE}/${name}`).then((r) => r.data),
    )
  }
  return staticCache.get(name)
}

/* ------------------------------------------------------------------ */
/* 字段归一化：甲的返回结构只要大致符合契约，前端都能吃下来            */
/* ------------------------------------------------------------------ */

function pick(obj, keys) {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null) return obj[k]
  }
  return undefined
}

function toItem(raw, index) {
  const movieId = Number(pick(raw, ['movieId', 'movie_id', 'itemId', 'item_id', 'mid']))
  const score = pick(raw, ['score', 'bpr', 'bpr_score', 'pred', 'value'])
  return {
    rank: Number(pick(raw, ['rank', 'position', 'idx']) ?? index + 1),
    movieId: Number.isFinite(movieId) ? movieId : null,
    score: score === undefined || score === null ? null : Number(score),
    genreAffinity: pick(raw, ['genreAffinity', 'genre_affinity']) ?? null,
    title: pick(raw, ['title', 'movieTitle', 'name']) ?? null,
    genres: pick(raw, ['genres', 'genre']) ?? null,
    year: pick(raw, ['year']) ?? null,
  }
}

/** 兼容裸数组 / {items} / {results} / {data} / {recommendations} 几种常见包装 */
export function normalizeItems(payload) {
  let list = payload
  if (!Array.isArray(list)) {
    list = pick(payload, ['items', 'results', 'recommendations', 'data', 'movies'])
  }
  if (!Array.isArray(list)) return []
  return list.map(toItem).filter((it) => it.movieId !== null).sort((a, b) => a.rank - b.rank)
}

/* ------------------------------------------------------------------ */
/* 对外接口                                                            */
/* ------------------------------------------------------------------ */

export async function fetchHealth() {
  if (MODE !== 'api') return null
  const { data, latencyMs } = await request(`${API_BASE}/health`, { timeout: 3000 })
  return { ...data, latencyMs }
}

export async function fetchMeta() {
  const meta = await loadStatic('meta.json')
  return { ...meta, source: MODE }
}

export async function fetchMetrics(force = false) {
  // 若甲额外实现了 /metrics，优先用接口；没有就退回仓库产出的静态指标
  if (MODE === 'api') {
    try {
      const { data } = await request(`${API_BASE}/metrics`, { timeout: 2500 })
      if (data && Array.isArray(data.models) && data.models.length) return { ...data, source: 'api' }
    } catch {
      /* 接口没有 /metrics 属于正常情况，静默回退 */
    }
  }
  if (force) staticCache.delete('metrics.json')
  const data = await loadStatic('metrics.json')
  return { ...data, source: 'static' }
}

export async function fetchMovieIndex() {
  return loadStatic('movies.json')
}

export async function fetchSampleUsers() {
  const snapshot = await loadStatic('recommend_static.json')
  return (snapshot.users || []).map((u) => u.userId)
}

/**
 * 单用户推荐。返回统一结构：
 *   { items, latencyMs, source, endpoint, model }
 * items 里已补齐电影名与类型（静态快照自带，接口结果用 movies.json 兜底）
 */
export async function predict(userId, topK = 10, movieIndex = null) {
  if (MODE === 'api') {
    try {
      const { data, latencyMs } = await request(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: Number(userId), topK: Number(topK) }),
        timeout: 8000,
      })
      const items = normalizeItems(data).slice(0, topK)
      return {
        items: await enrich(items, movieIndex),
        latencyMs,
        source: 'api',
        endpoint: 'POST /predict',
        model: pick(data, ['model', 'modelVersion', 'model_version']) ?? null,
      }
    } catch (err) {
      // 接口挂了不要让页面开天窗：退回本地快照，并如实标注回退原因
      const local = await predictStatic(userId, topK, movieIndex)
      return { ...local, fallback: true, fallbackReason: String(err.message || err) }
    }
  }
  return predictStatic(userId, topK, movieIndex)
}

async function predictStatic(userId, topK, movieIndex) {
  // 静态模式：从样例快照里取该用户的 Top10
  const snapshot = await loadStatic('recommend_static.json')
  const started = performance.now()
  const hit = (snapshot.users || []).find((u) => Number(u.userId) === Number(userId))
  const latencyMs = performance.now() - started
  if (!hit) {
    return {
      items: [],
      latencyMs,
      source: 'static',
      endpoint: 'public/data/recommend_static.json',
      model: null,
      missing: true,
    }
  }
  const items = hit.items.slice(0, topK).map((it) => ({
    rank: it.rank,
    movieId: it.movieId,
    score: it.score,
    genreAffinity: it.genreAffinity ?? null,
    title: it.title,
    genres: it.genres,
    year: it.year,
  }))
  return {
    items: await enrich(items, movieIndex),
    latencyMs,
    source: 'static',
    endpoint: 'public/data/recommend_static.json',
    model: null,
  }
}

/** 接口只回 movieId 时，用本地电影词表补齐片名与类型 */
async function enrich(items, movieIndex) {
  let index = movieIndex
  if (!index) {
    try {
      index = await fetchMovieIndex()
    } catch {
      index = {}
    }
  }
  return items.map((it) => {
    const meta = index[String(it.movieId)]
    const genres = it.genres
      ? Array.isArray(it.genres)
        ? it.genres
        : String(it.genres).split('|')
      : meta?.genres || []
    return {
      ...it,
      title: it.title || meta?.title || `MovieLens #${it.movieId}`,
      year: it.year ?? meta?.year ?? null,
      genres,
      hasMeta: Boolean(meta || it.title),
    }
  })
}
