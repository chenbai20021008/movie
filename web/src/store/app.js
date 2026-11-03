import { computed, reactive } from 'vue'
import {
  dataSource,
  fetchHealth,
  fetchMeta,
  fetchMetrics,
  fetchMovieIndex,
  fetchSampleUsers,
  predict,
} from '../api/client'

/** 全局状态：两个视图共用同一份元信息、指标与性能采样 */
export const store = reactive({
  ready: false,
  error: '',
  source: dataSource,
  meta: null,
  metrics: null,
  movies: {},
  users: [],
  apiOnline: null,
  health: null,
  perf: [],
  inflight: false,
})

let bootstrapping = null

export function bootstrap() {
  if (!bootstrapping) bootstrapping = runBootstrap()
  return bootstrapping
}

async function runBootstrap() {
  try {
    const [meta, metrics, movies, users] = await Promise.all([
      fetchMeta(),
      fetchMetrics(),
      fetchMovieIndex().catch(() => ({})),
      fetchSampleUsers(),
    ])
    store.meta = meta
    store.metrics = metrics
    store.movies = movies
    store.users = users
    store.ready = true

    if (store.source === 'api') {
      try {
        store.health = await fetchHealth()
        store.apiOnline = true
      } catch (err) {
        store.apiOnline = false
        store.health = { error: String(err.message || err) }
      }
    }
  } catch (err) {
    store.error = String(err?.message || err)
  }
}

/** 指标刷新：看板右上角的「刷新」按钮，绕过前端缓存重新读一次 */
export async function reloadMetrics() {
  const m = await fetchMetrics(true)
  store.metrics = m
}

/** 跑一次单用户推荐，并把耗时记进性能采样 */
export async function runPredict(userId, topK = 10) {
  store.inflight = true
  try {
    const result = await predict(userId, topK, store.movies)
    pushPerf({ latency: result.latencyMs, source: result.source, at: Date.now() })
    return result
  } finally {
    store.inflight = false
  }
}

export function pushPerf(sample) {
  store.perf.push(sample)
  if (store.perf.length > 60) store.perf.splice(0, store.perf.length - 60)
}

function quantile(sorted, q) {
  if (!sorted.length) return null
  const pos = (sorted.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  const next = sorted[base + 1]
  return next === undefined ? sorted[base] : sorted[base] + rest * (next - sorted[base])
}

/** p50 / p95 / 串行吞吐（1 / p50），全部来自真实采样，不做平滑 */
export const perfStats = computed(() => {
  const samples = store.perf.map((s) => s.latency).sort((a, b) => a - b)
  if (!samples.length) {
    return { count: 0, p50: null, p95: null, min: null, max: null, throughput: null, last: null }
  }
  const p50 = quantile(samples, 0.5)
  return {
    count: samples.length,
    p50,
    p95: quantile(samples, 0.95),
    min: samples[0],
    max: samples[samples.length - 1],
    throughput: p50 ? 1000 / p50 : null,
    last: store.perf[store.perf.length - 1],
  }
})

/** 离线批量吞吐：直接用 results/metrics_ranker_full.json 记录的 191,007 用户 / 61.7 s 推算 */
export const offlineThroughput = computed(() => {
  const m = store.metrics?.models?.find((x) => x.key === 'ranker_full')
  if (!m?.users) return null
  return { users: m.users, seconds: 61.7, perSecond: Math.round(m.users / 61.7) }
})
