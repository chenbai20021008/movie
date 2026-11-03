<script setup>
import { computed } from 'vue'
import { ms } from '../utils/labels'

const props = defineProps({
  stats: { type: Object, required: true },
  samples: { type: Array, default: () => [] },
  source: { type: String, default: 'static' },
  offline: { type: Object, default: null },
  endpoint: { type: String, default: '' },
})

const recent = computed(() => props.samples.slice(-24).map((s) => s.latency))
const isApi = computed(() => props.source === 'api')

const spark = computed(() => {
  const vals = recent.value
  if (vals.length < 2) return null
  const w = 132
  const h = 30
  const max = Math.max(...vals)
  const min = Math.min(...vals)
  const span = max - min || 1
  const step = w / (vals.length - 1)
  const pts = vals.map((v, i) => [i * step, h - ((v - min) / span) * (h - 4) - 2])
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
  const area = `${d} L${w},${h} L0,${h} Z`
  const last = pts[pts.length - 1]
  return { d, area, last, w, h }
})

const throughputText = computed(() => {
  if (!props.stats.throughput) return '—'
  return props.stats.throughput >= 1000
    ? `${(props.stats.throughput / 1000).toFixed(1)}k`
    : props.stats.throughput.toFixed(0)
})
</script>

<template>
  <section class="perf card">
    <div class="perf-head">
      <div>
        <h3>性能信息</h3>
        <p>{{ isApi ? '实测：浏览器到服务的往返耗时，逐次累加采样' : '当前为静态样例，延迟只含本地快照读取；接上接口后自动变为真实推理延迟' }}</p>
      </div>
      <code class="mono endpoint">{{ endpoint || '—' }}</code>
    </div>

    <div class="perf-grid">
      <div class="stat">
        <span>本次</span>
        <b class="num">{{ ms(stats.last?.latency) }}</b>
      </div>
      <div class="stat">
        <span>p50</span>
        <b class="num">{{ ms(stats.p50) }}</b>
      </div>
      <div class="stat">
        <span>p95</span>
        <b class="num">{{ ms(stats.p95) }}</b>
      </div>
      <div class="stat">
        <span>{{ isApi ? '串行吞吐' : '离线批量' }}</span>
        <b class="num">
          {{ isApi ? `${throughputText} rps` : offline ? `${(offline.perSecond / 1000).toFixed(1)}k /s` : '—' }}
        </b>
      </div>

      <div class="spark">
        <span class="spark-label">最近 {{ stats.count }} 次</span>
        <svg v-if="spark" :viewBox="`0 0 ${spark.w} ${spark.h}`" :width="spark.w" :height="spark.h">
          <path :d="spark.area" fill="rgba(47,107,237,.1)" />
          <path :d="spark.d" fill="none" stroke="#2f6bed" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" />
          <circle :cx="spark.last[0]" :cy="spark.last[1]" r="2.4" fill="#2f6bed" />
        </svg>
        <svg v-else viewBox="0 0 132 30" width="132" height="30" class="spark-empty">
          <line x1="0" y1="16" x2="132" y2="16" stroke="#e3e9f3" stroke-dasharray="3 3" />
        </svg>
      </div>
    </div>
  </section>
</template>

<style scoped>
.perf {
  padding: 15px 18px 16px;
}

.perf-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.perf-head h3 {
  font-size: 13.5px;
  font-weight: 640;
}

.perf-head p {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--text-3);
  max-width: 620px;
  line-height: 1.45;
}

.endpoint {
  font-size: 10.5px;
  color: var(--text-3);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 3px 7px;
  white-space: nowrap;
}

.perf-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr)) auto;
  align-items: center;
  gap: 18px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 12px;
  border-left: 2px solid var(--surface-3);
}

.stat span {
  font-size: 11px;
  color: var(--text-3);
}

.stat b {
  font-size: 17px;
  font-weight: 660;
  letter-spacing: -0.02em;
  color: var(--text);
}

.spark {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.spark-label {
  font-size: 10.5px;
  color: var(--text-3);
}

@media (max-width: 1080px) {
  .perf-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .spark {
    display: none;
  }
}
</style>
