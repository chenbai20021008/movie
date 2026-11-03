<script setup>
import { computed } from 'vue'
import { buildReason, fixed, genreCN, splitTitle } from '../utils/labels'

const props = defineProps({
  item: { type: Object, required: true },
  index: { type: Number, default: 0 },
  maxScore: { type: Number, default: null },
  minScore: { type: Number, default: null },
  candidates: { type: Number, default: 0 },
})

const title = computed(() => splitTitle(props.item.title))
const year = computed(() => props.item.year ?? title.value.year)
const genres = computed(() => (props.item.genres || []).filter(Boolean))
const top3 = computed(() => props.item.rank <= 3)
const hasAff = computed(() => props.item.genreAffinity !== null && props.item.genreAffinity !== undefined)

const scoreWidth = computed(() => {
  const { score } = props.item
  if (score === null || props.maxScore === null) return 0
  const lo = Math.min(props.minScore ?? 0, 0)
  const span = props.maxScore - lo || 1
  const v = ((score - lo) / span) * 100
  return Math.max(4, Math.min(100, v))
})

const reason = computed(() =>
  buildReason(props.item, { maxScore: props.maxScore, candidates: props.candidates, genres: genres.value }),
)

const affText = computed(() => (hasAff.value ? Number(props.item.genreAffinity).toFixed(3) : '待接入'))
</script>

<template>
  <article class="movie fade-up" :style="{ animationDelay: `${index * 26}ms` }">
    <div class="rank" :class="{ top: top3 }">
      <span class="num">{{ item.rank }}</span>
    </div>

    <div class="body">
      <div class="head">
        <h4 :title="item.title">{{ title.name }}</h4>
        <div class="score num" :class="{ negative: item.score !== null && item.score < 0 }">
          {{ item.score === null ? '—' : fixed(item.score, 4) }}
        </div>
      </div>

      <div class="tags">
        <span v-if="year" class="year num">{{ year }}</span>
        <span v-for="g in genres.slice(0, 3)" :key="g" class="chip chip-soft">{{ genreCN(g) }}</span>
        <span v-if="genres.length > 3" class="chip chip-soft more">+{{ genres.length - 3 }}</span>
        <span v-if="!item.hasMeta" class="chip chip-warn">元数据缺失</span>
      </div>

      <div class="bar" :title="`BPR 召回分 ${item.score ?? '—'}`">
        <div class="bar-fill" :style="{ width: `${scoreWidth}%` }" />
      </div>

      <div class="foot">
        <span class="aff" :class="{ off: !hasAff }">
          类型亲和度 <b class="num">{{ affText }}</b>
        </span>
        <span class="sep">·</span>
        <span class="mid num">#{{ item.movieId }}</span>
      </div>

      <p class="reason">{{ reason }}</p>
    </div>
  </article>
</template>

<style scoped>
.movie {
  position: relative;
  display: flex;
  gap: 13px;
  padding: 15px 16px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
  overflow: hidden;
}

.movie::after {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: linear-gradient(180deg, var(--primary), var(--cyan));
  opacity: 0;
  transition: opacity 0.18s ease;
}

.movie:hover {
  transform: translateY(-2px);
  border-color: #cfdbee;
  box-shadow: var(--shadow-lg);
}

.movie:hover::after {
  opacity: 1;
}

.rank {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: var(--surface-3);
  color: var(--text-3);
  font-size: 13px;
  font-weight: 680;
}

.rank.top {
  color: #fff;
  background: linear-gradient(155deg, #5b8bf7, var(--primary) 60%, #1f4fc4);
  box-shadow: 0 6px 14px -8px rgba(47, 107, 237, 0.9);
}

.body {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.head h4 {
  font-size: 14px;
  font-weight: 620;
  line-height: 1.35;
  letter-spacing: -0.005em;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.score {
  margin-left: auto;
  font-size: 13.5px;
  font-weight: 640;
  color: var(--primary-deep);
  flex: none;
}

.score.negative {
  color: var(--text-3);
}

.tags {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.year {
  font-size: 11.5px;
  color: var(--text-3);
  padding-right: 2px;
}

.bar {
  height: 4px;
  border-radius: 999px;
  background: var(--surface-3);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #7aa5f8, var(--primary) 70%, #1f4fc4);
  transition: width 0.5s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.foot {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--text-3);
}

.aff b {
  color: var(--text-2);
  font-weight: 620;
}

.aff.off b {
  color: var(--text-3);
  font-weight: 500;
}

.sep {
  color: var(--border-strong);
}

.reason {
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-2);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
