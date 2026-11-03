<script setup>
import { computed, onMounted, ref } from 'vue'
import KpiCard from '../components/KpiCard.vue'
import { CHART_FONT, useChart } from '../composables/useChart'
import { bootstrap, reloadMetrics, store } from '../store/app'
import { fixed, thousands } from '../utils/labels'

const modelEl = ref(null)
const ablationEl = ref(null)
const importanceEl = ref(null)
const refreshing = ref(false)

const metrics = computed(() => store.metrics)
const models = computed(() => metrics.value?.models || [])
const baseline = computed(() => metrics.value?.baseline || 0)
const targetNdcg = computed(() => metrics.value?.targetNdcg || 0)
const finalModel = computed(() => models.value.find((m) => m.final) || models.value[models.value.length - 1])
const improvement = computed(() =>
  finalModel.value && baseline.value ? ((finalModel.value.ndcg - baseline.value) / baseline.value) * 100 : null,
)

const improvementText = computed(() =>
  improvement.value === null ? '—' : `+${improvement.value.toFixed(1)}%`,
)

const AXIS_COLOR = '#8a99ae'
const SPLIT_COLOR = '#eef2f9'

const baseTooltip = {
  backgroundColor: 'rgba(255,255,255,.97)',
  borderColor: '#e3e9f3',
  borderWidth: 1,
  padding: [10, 12],
  textStyle: { color: '#0d1826', fontSize: 12, fontFamily: CHART_FONT },
  extraCssText: 'border-radius:10px;box-shadow:0 12px 32px -16px rgba(13,24,38,.4);',
}

const gradientBar = (from, to) => ({
  type: 'linear',
  x: 0,
  y: 0,
  x2: 0,
  y2: 1,
  colorStops: [
    { offset: 0, color: from },
    { offset: 1, color: to },
  ],
})

/* ---------------- 六模型 NDCG 柱状 + 相对提升折线 ---------------- */
const modelOption = computed(() => {
  if (!models.value.length) return null
  const names = models.value.map((m) => m.short)
  const ndcg = models.value.map((m) => ({
    value: m.ndcg,
    itemStyle: {
      borderRadius: [7, 7, 2, 2],
      color: m.final ? gradientBar('#4c86f7', '#1f4fc4') : gradientBar('#cbdcf8', '#a9c4ee'),
    },
  }))
  const gains = models.value.map((m) => (baseline.value ? Number((((m.ndcg - baseline.value) / baseline.value) * 100).toFixed(1)) : 0))

  return {
    textStyle: { fontFamily: CHART_FONT },
    grid: { left: 6, right: 10, top: 46, bottom: 6, containLabel: true },
    tooltip: {
      ...baseTooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(47,107,237,.05)' } },
      formatter: (params) => {
        const idx = params[0].dataIndex
        const m = models.value[idx]
        const rows = [
          `<div style="font-weight:640;margin-bottom:6px">${m.name}</div>`,
          `<div style="color:#55657c;font-size:11px;margin-bottom:6px">${m.task} · 评估用户 ${thousands(m.users)}${m.sampled ? '（抽样）' : ''}</div>`,
          `<div>NDCG@10 <b style="float:right;margin-left:16px">${fixed(m.ndcg)}</b></div>`,
        ]
        if (m.recall !== null) rows.push(`<div>Recall@10 <b style="float:right;margin-left:16px">${fixed(m.recall)}</b></div>`)
        if (m.mrr !== null) rows.push(`<div>MRR@10 <b style="float:right;margin-left:16px">${fixed(m.mrr)}</b></div>`)
        rows.push(`<div style="margin-top:6px;padding-top:6px;border-top:1px dashed #e3e9f3;color:#1f4fc4">相对热门 <b>${gains[idx] >= 0 ? '+' : ''}${gains[idx]}%</b></div>`)
        if (m.note) rows.push(`<div style="margin-top:5px;color:#8a99ae;font-size:11px;max-width:230px;line-height:1.45">${m.note}</div>`)
        return rows.join('')
      },
    },
    xAxis: {
      type: 'category',
      data: names,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e3e9f3' } },
      axisLabel: { color: '#55657c', fontSize: 11.5, interval: 0, margin: 12 },
    },
    yAxis: [
      {
        type: 'value',
        name: 'NDCG@10',
        min: 0.7,
        max: 0.92,
        interval: 0.05,
        nameTextStyle: { color: AXIS_COLOR, fontSize: 10.5, padding: [0, 0, 6, 0] },
        axisLabel: { color: AXIS_COLOR, fontSize: 10.5, formatter: (v) => v.toFixed(2) },
        splitLine: { lineStyle: { color: SPLIT_COLOR } },
      },
      {
        type: 'value',
        name: '相对热门',
        min: 0,
        max: 26,
        nameTextStyle: { color: AXIS_COLOR, fontSize: 10.5, padding: [0, 0, 6, 0] },
        axisLabel: { color: AXIS_COLOR, fontSize: 10.5, formatter: '{value}%' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'NDCG@10',
        type: 'bar',
        barWidth: 38,
        data: ndcg,
        label: {
          show: true,
          position: 'top',
          distance: 7,
          color: '#0d1826',
          fontSize: 11.5,
          fontWeight: 620,
          formatter: (p) => p.value.toFixed(4),
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#0f9d63', type: 'dashed', width: 1.2, opacity: 0.8 },
          label: {
            formatter: `任务书目标 ${targetNdcg.value.toFixed(4)}（+10%）`,
            position: 'insideStartTop',
            color: '#0f9d63',
            fontSize: 10,
            backgroundColor: 'rgba(230,247,239,.9)',
            padding: [2, 5],
            borderRadius: 4,
          },
          data: [{ yAxis: targetNdcg.value }],
        },
      },
      {
        name: '相对热门',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: gains,
        lineStyle: { color: '#0bb6d4', width: 1.8 },
        itemStyle: { color: '#fff', borderColor: '#0bb6d4', borderWidth: 2 },
        tooltip: { show: false },
        z: 5,
      },
    ],
  }
})

/* ---------------- 消融实验 ---------------- */
const ablationOption = computed(() => {
  const rows = metrics.value?.ablation || []
  if (!rows.length) return null
  const full = rows[0].ndcg
  return {
    textStyle: { fontFamily: CHART_FONT },
    grid: { left: 4, right: 16, top: 26, bottom: 4, containLabel: true },
    tooltip: {
      ...baseTooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(47,107,237,.05)' } },
      formatter: (params) => {
        const m = rows[params[0].dataIndex]
        const d = ((m.ndcg - full) / full) * 100
        return `<div style="font-weight:640;margin-bottom:4px">${m.name}</div>
          <div>NDCG@10 <b style="float:right;margin-left:16px">${fixed(m.ndcg)}</b></div>
          <div>相对完整模型 <b style="float:right;margin-left:16px;color:${d < 0 ? '#d64545' : '#0f9d63'}">${d >= 0 ? '+' : ''}${d.toFixed(1)}%</b></div>`
      },
    },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.name),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e3e9f3' } },
      axisLabel: { color: '#55657c', fontSize: 11, interval: 0, margin: 10 },
    },
    yAxis: {
      type: 'value',
      min: 0.8,
      max: 0.94,
      interval: 0.02,
      axisLabel: { color: AXIS_COLOR, fontSize: 10.5, formatter: (v) => v.toFixed(2) },
      splitLine: { lineStyle: { color: SPLIT_COLOR } },
    },
    series: [
      {
        type: 'bar',
        barWidth: 46,
        data: rows.map((r, i) => ({
          value: r.ndcg,
          itemStyle: {
            borderRadius: [7, 7, 2, 2],
            color: i === 0 ? gradientBar('#4c86f7', '#1f4fc4') : gradientBar('#dfe8f8', '#bfd2ef'),
          },
        })),
        label: {
          show: true,
          position: 'top',
          distance: 7,
          formatter: (p) => {
            const d = ((p.value - full) / full) * 100
            if (Math.abs(d) < 0.05) return `{v|${p.value.toFixed(4)}}\n{d0|完整模型}`
            return `{v|${p.value.toFixed(4)}}\n{dn|${d.toFixed(1)}%}`
          },
          rich: {
            v: { fontSize: 11.5, fontWeight: 640, color: '#0d1826', lineHeight: 15 },
            dn: { fontSize: 10.5, fontWeight: 600, color: '#d64545', lineHeight: 13 },
            d0: { fontSize: 10.5, color: '#8a99ae', lineHeight: 13 },
          },
        },
      },
    ],
  }
})

/* ---------------- 特征重要性（对数轴） ---------------- */
const importanceOption = computed(() => {
  const rows = (metrics.value?.featureImportance || []).filter((r) => r.gain > 0)
  if (!rows.length) return null
  const sorted = [...rows].sort((a, b) => a.gain - b.gain)
  return {
    textStyle: { fontFamily: CHART_FONT },
    grid: { left: 4, right: 56, top: 8, bottom: 20, containLabel: true },
    tooltip: {
      ...baseTooltip,
      trigger: 'item',
      formatter: (p) => {
        const r = sorted[p.dataIndex]
        const total = rows.reduce((s, x) => s + x.gain, 0)
        return `<div style="font-weight:640;margin-bottom:4px">${r.label}</div>
          <div>分裂增益 <b style="float:right;margin-left:16px">${thousands(Math.round(r.gain))}</b></div>
          <div style="color:#55657c">占比 ${((r.gain / total) * 100).toFixed(1)}%</div>`
      },
    },
    xAxis: {
      type: 'log',
      min: 100,
      max: 1e6,
      axisLabel: {
        color: AXIS_COLOR,
        fontSize: 10,
        formatter: (v) => (v >= 1e6 ? '1M' : v >= 1000 ? `${v / 1000}k` : v),
      },
      splitLine: { lineStyle: { color: SPLIT_COLOR } },
      axisLine: { show: false },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((r) => r.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e3e9f3' } },
      axisLabel: { color: '#55657c', fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        barWidth: 13,
        data: sorted.map((r, i) => ({
          value: r.gain,
          itemStyle: {
            borderRadius: [2, 7, 7, 2],
            color: i === sorted.length - 1 ? gradientBar('#4c86f7', '#1f4fc4') : '#c3d4f0',
          },
        })),
        label: {
          show: true,
          position: 'right',
          distance: 8,
          color: '#55657c',
          fontSize: 10.5,
          formatter: (p) => thousands(Math.round(p.value)),
        },
      },
    ],
  }
})

useChart(modelEl, () => modelOption.value, () => models.value)
useChart(ablationEl, () => ablationOption.value, () => metrics.value)
useChart(importanceEl, () => importanceOption.value, () => metrics.value)

const taskCards = computed(() => {
  const t = metrics.value?.tasks || {}
  const out = []
  if (t.streaming) {
    out.push({
      key: 'streaming',
      tag: '任务四 · 流式增量',
      value: `${thousands(t.streaming.throughput)}`,
      unit: '事件/秒',
      rows: [
        ['窗口数', thousands(t.streaming.windows)],
        ['单次更新', `${t.streaming.avgUpdateUs} µs`],
        ['与批量一致', t.streaming.consistency ? '是' : '否'],
      ],
    })
  }
  if (t.als) {
    const alsModel = models.value.find((m) => m.key === 'als')
    out.push({
      key: 'als',
      tag: '任务三 · Spark ALS',
      value: fixed(alsModel?.ndcg ?? t.als.ndcg),
      unit: 'NDCG@10',
      rows: [
        ['引擎', `${t.als.engine || 'ALS'} ${t.als.sparkVersion || ''}`],
        ['训练耗时', `${t.als.fitSeconds} s`],
        ['抽样用户', thousands(t.als.users)],
        ['报告 5 轮 run', fixed(t.als.ndcg)],
      ],
    })
  }
  if (t.lsh) {
    out.push({
      key: 'lsh',
      tag: '任务二 · 相似度 + LSH',
      value: fixed(t.lsh.recallAtK, 3),
      unit: 'recall@20',
      rows: [
        ['平均候选', t.lsh.avgCandidates?.toFixed(1)],
        ['加速比', `${t.lsh.speedup?.toFixed(1)}×`],
        ['头部条目', thousands(t.lsh.headItems)],
      ],
    })
  }
  if (t.graph) {
    out.push({
      key: 'graph',
      tag: '任务五 · 二部图链接',
      value: fixed(t.graph.ndcgCommunity || 0),
      unit: 'NDCG@10',
      rows: [
        ['社区数', t.graph.communities],
        ['模块度', t.graph.modularity?.toFixed(4)],
        ['图节点', thousands(t.graph.nodes)],
      ],
    })
  }
  return out
})

const tableRows = computed(() =>
  models.value.map((m) => ({
    ...m,
    // 热门基线是自己跟自己比，不显示提升幅度
    gain:
      baseline.value && m.key !== 'popularity'
        ? (((m.ndcg - baseline.value) / baseline.value) * 100).toFixed(1)
        : null,
    isBaseline: m.key === 'popularity',
  })),
)

const protocol = computed(() => metrics.value?.protocol || {})

async function refresh() {
  refreshing.value = true
  try {
    await reloadMetrics()
  } finally {
    refreshing.value = false
  }
}

onMounted(async () => {
  await bootstrap()
})
</script>

<template>
  <section class="page">
    <div class="page-head">
      <div>
        <span class="eyebrow">指标看板</span>
        <h1>六个模型、三组消融：提升到底从哪来</h1>
        <p class="lede">
          数据来自 <code class="mono">results/metrics_*.json</code> 与各专题报告，接口就绪后同一套图表也能读
          <code class="mono">/metrics</code>。
        </p>
      </div>
      <div class="head-actions">
        <span class="chip chip-soft" v-if="metrics">
          <i class="dot" style="color: var(--success)" />
          生成于 {{ metrics.generatedAt }}
        </span>
        <button class="btn" :disabled="refreshing" @click="refresh">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.9">
            <path d="M20 11a8 8 0 1 0-2.3 5.7" stroke-linecap="round" />
            <path d="M20 5v6h-6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          {{ refreshing ? '刷新中' : '刷新' }}
        </button>
      </div>
    </div>

    <!-- 概览 -->
    <div class="kpis">
      <KpiCard hero title="最终 NDCG@10" :sub="`热门基线 ${fixed(baseline)} → 集成排序 ${fixed(finalModel?.ndcg)}`">
        <span class="num">{{ fixed(finalModel?.ndcg) }}</span>
        <small>NDCG@10</small>
      </KpiCard>
      <KpiCard title="相对热门提升" :sub="`任务书要求 ≥ 10%，实际 ${improvementText}`">
        <span class="num">{{ improvement === null ? '—' : `+${improvement.toFixed(1)}` }}</span>
        <small>%</small>
      </KpiCard>
      <KpiCard title="Recall@10" :sub="`同批 ${thousands(finalModel?.users)} 位用户`">
        <span class="num">{{ fixed(finalModel?.recall) }}</span>
        <small>Recall@10</small>
      </KpiCard>
      <KpiCard title="MRR@10" :sub="`单用户离线打分 ${finalModel?.perUserMs ?? '—'} ms`">
        <span class="num">{{ fixed(finalModel?.mrr) }}</span>
        <small>MRR@10</small>
      </KpiCard>
    </div>

    <!-- 主图 -->
    <section class="panel main-chart">
      <div class="panel-head">
        <div>
          <h3>六个模型的 NDCG@10 与相对提升</h3>
          <p class="sub">
            柱=NDCG@10（左轴）· 折线=相对热门基线提升（右轴）· 绿色虚线=任务书「不低于 10%」的目标线
          </p>
        </div>
        <span class="chip chip-primary">同一候选集口径</span>
      </div>
      <div ref="modelEl" class="chart chart-lg" />
    </section>

    <!-- 消融 + 特征重要性 -->
    <div class="two-col">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>消融实验</h3>
            <p class="sub">去掉单个特征后重训，看它到底贡献了多少</p>
          </div>
        </div>
        <div ref="ablationEl" class="chart chart-md" />
        <p class="foot-note">BPR 召回分贡献 −5.4%，类型亲和度贡献 −1.9%；两者都不可替代。</p>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>LightGBM 特征重要性</h3>
            <p class="sub">按分裂增益排序（对数轴）：BPR 分数一枝独秀，其余是修正项</p>
          </div>
        </div>
        <div ref="importanceEl" class="chart chart-md tall" />
        <p class="foot-note">pop_log 与 item_bayes 的增益为 0，说明树模型未在它们上分裂。</p>
      </section>
    </div>

    <!-- 各任务指标 -->
    <div class="task-grid">
      <article v-for="card in taskCards" :key="card.key" class="task card">
        <span class="tag">{{ card.tag }}</span>
        <div class="big">
          <b class="num">{{ card.value }}</b>
          <span>{{ card.unit }}</span>
        </div>
        <dl>
          <div v-for="[k, v] in card.rows" :key="k">
            <dt>{{ k }}</dt>
            <dd class="num">{{ v }}</dd>
          </div>
        </dl>
      </article>
    </div>

    <!-- 明细表 -->
    <section class="panel">
      <div class="panel-head">
        <div>
          <h3>模型明细</h3>
          <p class="sub">同一协议下的完整对照；抽样评估的模型已标注，横向比较时需注意样本量差异</p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>模型</th>
              <th>任务</th>
              <th class="r">NDCG@10</th>
              <th class="r">Recall@10</th>
              <th class="r">MRR@10</th>
              <th class="r">相对热门</th>
              <th class="r">评估用户</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in tableRows" :key="row.key" :class="{ final: row.final }">
              <td>
                <span class="name">{{ row.name }}</span>
                <span v-if="row.sampled" class="chip chip-warn mini">抽样</span>
              </td>
              <td class="muted">{{ row.task }}</td>
              <td class="r num strong">{{ fixed(row.ndcg) }}</td>
              <td class="r num">{{ fixed(row.recall) }}</td>
              <td class="r num">{{ fixed(row.mrr) }}</td>
              <td class="r num" :class="row.isBaseline ? 'muted' : Number(row.gain) > 0 ? 'up' : 'muted'">
                {{ row.isBaseline ? '基准' : row.gain === null ? '—' : `${Number(row.gain) > 0 ? '+' : ''}${row.gain}%` }}
              </td>
              <td class="r num muted">{{ thousands(row.users) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p class="protocol">
      <strong>口径：</strong>{{ protocol.dataset }} · {{ thousands(protocol.ratings) }} 条评分 · 正反馈 {{ protocol.positive }} ·
      {{ protocol.split }} · {{ protocol.candidates }} · 主指标 {{ protocol.primary }}。
      Spark ALS 与二部图实验在 20k 用户抽样上完成，单独看绝对分数偏低不代表方法更弱。
    </p>
  </section>
</template>

<style scoped>
.lede code,
.protocol code {
  font-size: 12px;
  background: var(--surface-3);
  padding: 1px 5px;
  border-radius: 5px;
  color: var(--text-2);
}

.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.main-chart {
  margin-bottom: 14px;
}

.chart {
  width: 100%;
}

.chart-lg {
  height: 330px;
  padding: 0 8px 6px;
}

.chart-md {
  height: 272px;
  padding: 0 8px 0;
}

.chart-md.tall {
  height: 272px;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
  align-items: stretch;
}

.two-col > .panel {
  display: flex;
  flex-direction: column;
}

.two-col > .panel .chart {
  flex: 1 1 auto;
}

.foot-note {
  padding: 0 20px 16px;
  font-size: 11.5px;
  color: var(--text-3);
  line-height: 1.55;
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.task {
  padding: 14px 16px 15px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tag {
  font-size: 11px;
  color: var(--text-3);
  font-weight: 560;
}

.big {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.big b {
  font-size: 21px;
  font-weight: 680;
  letter-spacing: -0.02em;
}

.big span {
  font-size: 11px;
  color: var(--text-3);
}

.task dl {
  margin: 2px 0 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task dl > div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11.5px;
}

.task dt {
  color: var(--text-3);
}

.task dd {
  margin: 0;
  color: var(--text-2);
  font-weight: 560;
}

.table-wrap {
  padding: 8px 8px 12px;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

th {
  text-align: left;
  font-weight: 560;
  font-size: 11px;
  color: var(--text-3);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--surface-3);
  color: var(--text-2);
}

tr:last-child td {
  border-bottom: none;
}

tr.final td {
  background: rgba(47, 107, 237, 0.035);
}

.name {
  color: var(--text);
  font-weight: 580;
}

.mini {
  margin-left: 6px;
  height: 18px;
  font-size: 10px;
}

.r {
  text-align: right;
}

.strong {
  color: var(--text);
  font-weight: 640;
}

.muted {
  color: var(--text-3);
}

.up {
  color: var(--success);
}

.protocol {
  margin-top: 16px;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--text-3);
  padding: 0 4px;
}

.protocol strong {
  color: var(--text-2);
}

@media (max-width: 1080px) {
  .kpis,
  .task-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .two-col {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .kpis,
  .task-grid {
    grid-template-columns: 1fr;
  }
  .chart-lg {
    height: 280px;
  }
}
</style>
