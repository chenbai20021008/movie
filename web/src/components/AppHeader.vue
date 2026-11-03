<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { store } from '../store/app'

const route = useRoute()

const nav = [
  { to: '/', label: '推荐展示', hint: '选用户 · 看 Top10' },
  { to: '/dashboard', label: '指标看板', hint: '六模型 · 消融 · 性能' },
]

const sourceLabel = computed(() => {
  if (store.source === 'api') {
    if (store.apiOnline === true) return '实时接口'
    if (store.apiOnline === false) return '接口离线'
    return '连接中'
  }
  return '静态样例'
})

const sourceTone = computed(() => {
  if (store.source === 'api') return store.apiOnline === false ? 'warn' : 'live'
  return 'static'
})
</script>

<template>
  <header class="app-header">
    <div class="bar">
      <RouterLink to="/" class="brand">
        <span class="mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="17" height="17">
            <path d="M8 6.4 17.2 12 8 17.6Z" fill="currentColor" />
          </svg>
        </span>
        <span class="brand-text">
          <strong>MovieRec</strong>
          <em>MovieLens 32M · 服务化演示</em>
        </span>
      </RouterLink>

      <nav class="tabs">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="tab" :class="{ active: route.path === item.to }">
          <span>{{ item.label }}</span>
          <small>{{ item.hint }}</small>
        </RouterLink>
      </nav>

      <div class="meta">
        <span class="src" :class="sourceTone">
          <i class="dot" />
          {{ sourceLabel }}
        </span>
        <span class="model" v-if="store.meta">ranker_full · 9 特征</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 30;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid rgba(227, 233, 243, 0.9);
}

.bar {
  max-width: 1320px;
  margin: 0 auto;
  height: 62px;
  padding: 0 32px;
  display: flex;
  align-items: center;
  gap: 26px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}

.mark {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(150deg, #4d86f7, var(--primary) 55%, #1f4fc4);
  box-shadow: 0 4px 12px -4px rgba(47, 107, 237, 0.7);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.brand-text strong {
  font-size: 14.5px;
  font-weight: 680;
  letter-spacing: -0.01em;
}

.brand-text em {
  font-size: 11px;
  font-style: normal;
  color: var(--text-3);
  letter-spacing: 0.01em;
}

.tabs {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 12px;
  background: var(--surface-3);
  border: 1px solid var(--border);
}

.tab {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 5px 14px;
  border-radius: 9px;
  color: var(--text-2);
  transition: all 0.16s ease;
  line-height: 1.2;
}

.tab span {
  font-size: 13px;
  font-weight: 560;
}

.tab small {
  font-size: 10.5px;
  color: var(--text-3);
}

.tab:hover {
  background: rgba(255, 255, 255, 0.7);
}

.tab.active {
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border);
  color: var(--text);
}

.tab.active small {
  color: var(--primary);
}

.meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.src {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 560;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-2);
}

.src.live {
  color: var(--success);
  background: var(--success-soft);
  border-color: rgba(15, 157, 99, 0.18);
}

.src.warn {
  color: var(--warn);
  background: var(--warn-soft);
  border-color: rgba(217, 119, 6, 0.18);
}

.src.static {
  color: var(--primary-deep);
  background: var(--primary-soft);
  border-color: rgba(47, 107, 237, 0.16);
}

.model {
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--text-3);
  padding-left: 10px;
  border-left: 1px solid var(--border);
}

@media (max-width: 900px) {
  .bar {
    padding: 0 18px;
    gap: 12px;
  }
  .brand-text em,
  .model {
    display: none;
  }
  .tab small {
    display: none;
  }
}
</style>
