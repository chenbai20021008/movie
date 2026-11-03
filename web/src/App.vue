<script setup>
import AppHeader from './components/AppHeader.vue'
</script>

<template>
  <div class="shell">
    <AppHeader />
    <RouterView v-slot="{ Component }">
      <Transition name="view" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
    <footer class="app-foot">
      <span>大数据技术课程项目 · 服务化阶段 · 成员乙（前端与可视化）</span>
      <span class="sep">·</span>
      <a href="https://github.com/happytt-maker/movie" target="_blank" rel="noreferrer">github.com/happytt-maker/movie</a>
    </footer>
  </div>
</template>

<style scoped>
.app-foot {
  max-width: 1320px;
  width: 100%;
  margin: 0 auto;
  padding: 8px 32px 28px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: var(--text-3);
}

.app-foot a {
  color: var(--text-3);
  border-bottom: 1px dotted var(--border-strong);
  transition: color 0.15s ease;
}

.app-foot a:hover {
  color: var(--primary);
  border-color: var(--primary);
}

.sep {
  opacity: 0.6;
}

@media (max-width: 720px) {
  .app-foot {
    padding: 4px 14px 20px;
  }
}
</style>
