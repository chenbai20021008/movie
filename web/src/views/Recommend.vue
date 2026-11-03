<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import MovieCard from '../components/MovieCard.vue'
import PerfStrip from '../components/PerfStrip.vue'
import UserPicker from '../components/UserPicker.vue'
import { bootstrap, offlineThroughput, perfStats, runPredict, store } from '../store/app'
import { ms } from '../utils/labels'

const userId = ref(null)
const items = ref([])
const result = ref(null)
const error = ref('')
const loading = ref(false)
let seq = 0

const topK = 10
const candidates = computed(() => store.meta?.candidatesPerUser || 101)

const maxScore = computed(() => (items.value.length ? Math.max(...items.value.map((i) => i.score ?? 0)) : null))
const minScore = computed(() => (items.value.length ? Math.min(...items.value.map((i) => i.score ?? 0)) : null))

const sourceLabel = computed(() => {
  if (!result.value) return '—'
  if (result.value.fallback) return '本地快照（接口回退）'
  return result.value.source === 'api' ? '实时接口' : '静态样例'
})

async function run() {
  if (userId.value === null) return
  const my = ++seq
  loading.value = true
  error.value = ''
  try {
    const res = await runPredict(userId.value, topK)
    if (my !== seq) return // 用户切得快，丢弃过期响应
    result.value = res
    items.value = res.items
    if (res.missing) {
      error.value = '该用户不在本地样例快照里。运行 web/scripts/export_web_data.py 重新导出，或把数据源切到接口。'
    }
  } catch (err) {
    if (my !== seq) return
    items.value = []
    result.value = null
    error.value = `请求失败：${err.message || err}`
  } finally {
    if (my === seq) loading.value = false
  }
}

function pickRandom() {
  const pool = store.users.filter((u) => u !== userId.value)
  const list = pool.length ? pool : store.users
  if (!list.length) return
  userId.value = list[Math.floor(Math.random() * list.length)]
}

onMounted(async () => {
  await bootstrap()
  if (!store.users.length) return
  // 默认落在导出脚本挑好的用户（Top10 分数跨度最大）上，首屏就能看清条形差异
  const preferred = store.meta?.defaultUser
  userId.value = store.users.includes(preferred)
    ? preferred
    : store.users[Math.floor(Math.random() * store.users.length)]
})

watch(userId, (v) => {
  if (v !== null) run()
})
</script>

<template>
  <section class="page">
    <div class="page-head">
      <div>
        <span class="eyebrow">推荐展示</span>
        <h1>选一个用户，看模型给他的 Top10</h1>
        <p class="lede">
          左栏挑测试用户，右栏是 <code class="mono">ranker_full</code> 输出的推荐结果。
          接口未就绪时读本地样例快照，甲的 FastAPI 上线后改一个环境变量即可切换。
        </p>
      </div>
      <div class="head-actions">
        <button class="btn" :disabled="loading || !userId" @click="run">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.9">
            <path d="M20 11a8 8 0 1 0-2.3 5.7" stroke-linecap="round" />
            <path d="M20 5v6h-6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          重新推理
        </button>
        <button class="btn btn-primary" :disabled="!store.users.length" @click="pickRandom">换一个用户</button>
      </div>
    </div>

    <div class="workspace">
      <UserPicker v-model="userId" :users="store.users" :disabled="loading" @random="pickRandom" />

      <div class="result">
        <!-- 本次请求摘要 -->
        <div class="summary card">
          <div class="who">
            <span class="avatar mono">#{{ userId ?? '—' }}</span>
            <div class="who-text">
              <strong>用户 {{ userId ?? '未选择' }}</strong>
              <p>候选集 {{ candidates }} 部 · 输出 Top{{ topK }} · 已排除训练集交互</p>
            </div>
          </div>
          <div class="facts">
            <div class="fact">
              <span>模型</span>
              <b class="mono">ranker_full</b>
            </div>
            <div class="fact">
              <span>本次延迟</span>
              <b class="num">{{ loading ? '…' : ms(result?.latencyMs) }}</b>
            </div>
            <div class="fact">
              <span>数据源</span>
              <b>{{ sourceLabel }}</b>
            </div>
          </div>
        </div>

        <!-- 结果列表 -->
        <div v-if="result?.fallback" class="notice">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.9">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v4.5M12 16h.01" stroke-linecap="round" />
          </svg>
          <span>接口不可用（{{ result.fallbackReason }}），已自动回退到本地快照，页面与答辩演示不受影响。</span>
        </div>

        <div v-if="loading && !items.length" class="grid">
          <div v-for="n in 10" :key="n" class="skeleton sk-card" />
        </div>

        <div v-else-if="error" class="empty card">
          <strong>没有拿到推荐结果</strong>
          <p>{{ error }}</p>
        </div>

        <div v-else class="grid">
          <MovieCard
            v-for="(item, idx) in items"
            :key="`${item.movieId}-${item.rank}`"
            :item="item"
            :index="idx"
            :max-score="maxScore"
            :min-score="minScore"
            :candidates="candidates"
          />
        </div>

        <PerfStrip
          :stats="perfStats"
          :samples="store.perf"
          :source="store.source"
          :offline="offlineThroughput"
          :endpoint="result?.endpoint"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.lede code {
  font-size: 12px;
  background: var(--surface-3);
  padding: 1px 5px;
  border-radius: 5px;
  color: var(--text-2);
}

.workspace {
  display: grid;
  grid-template-columns: 272px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.result {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.summary {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 13px 18px;
  flex-wrap: wrap;
}

.who {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.avatar {
  height: 38px;
  min-width: 62px;
  padding: 0 10px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 680;
  color: #fff;
  background: linear-gradient(150deg, #5b8bf7, var(--primary) 58%, #1f4fc4);
  box-shadow: 0 8px 18px -12px rgba(47, 107, 237, 0.95);
}

.who-text strong {
  font-size: 14px;
  font-weight: 640;
  display: block;
}

.who-text p {
  margin-top: 2px;
  font-size: 11.5px;
  color: var(--text-3);
}

.facts {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 18px;
}

.fact {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-left: 18px;
  border-left: 1px solid var(--border);
}

.fact span {
  font-size: 10.5px;
  color: var(--text-3);
}

.fact b {
  font-size: 12.5px;
  font-weight: 620;
  color: var(--text);
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 13px;
  border-radius: 11px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--warn);
  background: var(--warn-soft);
  border: 1px solid rgba(217, 119, 6, 0.2);
}

.notice svg {
  flex: none;
  margin-top: 1px;
}

.sk-card {
  height: 132px;
}

.empty p {
  max-width: 520px;
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .workspace :deep(.picker) {
    position: static;
  }
  .workspace :deep(.list) {
    max-height: 190px;
  }
}

@media (max-width: 820px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .facts {
    margin-left: 0;
    width: 100%;
    gap: 12px;
  }
  .fact:first-child {
    padding-left: 0;
    border-left: none;
  }
}
</style>
