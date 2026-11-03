<script setup>
defineProps({
  title: { type: String, required: true },
  sub: { type: String, default: '' },
  tone: { type: String, default: 'plain' },
})
</script>

<template>
  <section class="kpi card" :class="tone">
    <header>
      <span class="label">{{ title }}</span>
      <slot name="badge" />
    </header>
    <div class="value">
      <slot />
    </div>
    <p v-if="sub" class="sub">{{ sub }}</p>
  </section>
</template>

<style scoped>
.kpi {
  padding: 15px 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
  overflow: hidden;
}

.kpi::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, rgba(47, 107, 237, 0.55), rgba(11, 182, 212, 0.15));
  opacity: 0;
  transition: opacity 0.2s ease;
}

.kpi.hero::before {
  opacity: 1;
}

header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 12px;
  color: var(--text-3);
  font-weight: 520;
}

.value {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 27px;
  font-weight: 680;
  letter-spacing: -0.03em;
  line-height: 1.1;
  color: var(--text);
}

.value :deep(small) {
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0;
  color: var(--text-3);
}

.sub {
  font-size: 11.5px;
  color: var(--text-3);
  line-height: 1.4;
}

.sub :deep(b) {
  color: var(--success);
  font-weight: 620;
}

.kpi.hero .value {
  color: var(--primary-deep);
}
</style>
