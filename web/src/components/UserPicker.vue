<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  users: { type: Array, default: () => [] },
  modelValue: { type: [Number, String], default: null },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'random'])

const keyword = ref('')
const listRef = ref(null)

const filtered = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return props.users
  return props.users.filter((u) => String(u).includes(kw))
})

function choose(uid) {
  emit('update:modelValue', Number(uid))
}

// 换用户后把选中项滚进可视区，避免选了 #180 却还停在列表顶部
watch(
  () => props.modelValue,
  async () => {
    await nextTick()
    const active = listRef.value?.querySelector('.row.active')
    active?.scrollIntoView({ block: 'nearest' })
  },
)
</script>

<template>
  <section class="picker card">
    <header class="picker-head">
      <div>
        <h3>测试用户</h3>
        <p>来自样本快照，共 {{ users.length }} 位</p>
      </div>
      <button class="btn btn-ghost" :disabled="disabled || !users.length" @click="emit('random')">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M16 3h5v5M21 3l-7 7M8 21H3v-5M3 21l7-7M21 16v5h-5M14 14l7 7M3 8V3h5M10 10L3 3" stroke-linecap="round" />
        </svg>
        随机抽取
      </button>
    </header>

    <div class="search">
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.2-3.2" stroke-linecap="round" />
      </svg>
      <input v-model="keyword" type="text" inputmode="numeric" placeholder="搜索 userId，例如 12" />
      <button v-if="keyword" class="clear" @click="keyword = ''" aria-label="清空">×</button>
    </div>

    <div ref="listRef" class="list" role="listbox">
      <button
        v-for="uid in filtered"
        :key="uid"
        class="row"
        :class="{ active: Number(modelValue) === Number(uid) }"
        role="option"
        :aria-selected="Number(modelValue) === Number(uid)"
        @click="choose(uid)"
      >
        <span class="id mono">#{{ uid }}</span>
        <span class="hint">Top10 已就绪</span>
        <svg class="arrow" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
          <path d="m9 6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>

      <p v-if="!filtered.length" class="no-hit">没有匹配的 userId</p>
    </div>

    <footer class="picker-foot">
      <span>数据源</span>
      <code class="mono">results/sample_top10.csv</code>
    </footer>
  </section>
</template>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  padding: 16px 16px 12px;
  position: sticky;
  top: 84px;
}

.picker-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.picker-head h3 {
  font-size: 14px;
  font-weight: 660;
}

.picker-head p {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--text-3);
}

.search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 10px;
  border-radius: 9px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-3);
  transition: border-color 0.16s ease, background 0.16s ease;
}

.search:focus-within {
  border-color: rgba(47, 107, 237, 0.4);
  background: var(--surface);
  box-shadow: 0 0 0 3px rgba(47, 107, 237, 0.09);
}

.search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 12.5px;
  color: var(--text);
}

.search input::placeholder {
  color: var(--text-3);
}

.clear {
  font-size: 15px;
  line-height: 1;
  color: var(--text-3);
  padding: 0 2px;
}

.list {
  margin: 10px -4px 6px;
  padding: 0 4px;
  max-height: 336px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  scrollbar-width: thin;
}

.list::-webkit-scrollbar {
  width: 6px;
}

.list::-webkit-scrollbar-thumb {
  background: #dce4f0;
  border-radius: 99px;
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 9px;
  border-radius: 9px;
  text-align: left;
  transition: background 0.14s ease;
  color: var(--text-2);
}

.row:hover {
  background: var(--surface-2);
}

.row.active {
  background: var(--primary-soft);
  color: var(--primary-deep);
}

.row .id {
  font-size: 12.5px;
  font-weight: 600;
}

.row .hint {
  font-size: 10.5px;
  color: var(--text-3);
  margin-left: auto;
}

.row.active .hint {
  color: rgba(31, 79, 196, 0.65);
}

.arrow {
  opacity: 0;
  transition: opacity 0.14s ease;
  flex: none;
}

.row:hover .arrow,
.row.active .arrow {
  opacity: 0.7;
}

.no-hit {
  padding: 18px 0;
  text-align: center;
  font-size: 12px;
  color: var(--text-3);
}

.picker-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
  font-size: 10.5px;
  color: var(--text-3);
}

.picker-foot code {
  font-size: 10px;
  color: var(--text-2);
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 5px;
  border: 1px solid var(--border);
}
</style>
