<template>
  <div class="stat-card">
    <div class="stat-top">
      <span class="stat-label">{{ label }}</span>
      <span class="stat-icon" :style="{ color, backgroundColor: `${color}1f` }">
        <el-icon :size="18"><component :is="icon" /></el-icon>
      </span>
    </div>
    <div class="stat-value">
      {{ value }}
      <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
    </div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    default: ''
  },
  value: {
    type: [String, Number],
    default: '-'
  },
  suffix: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  },
  icon: {
    type: [Object, Function],
    default: null
  },
  color: {
    type: String,
    default: '#4f7cff'
  }
})
</script>

<style scoped>
.stat-card {
  position: relative;
  padding: 17px 18px 15px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 6px 22px rgba(23, 43, 99, 0.045);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card::after {
  content: '';
  position: absolute;
  right: -26px;
  top: -26px;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(79, 124, 255, 0.08), transparent 70%);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(23, 43, 99, 0.08);
}

.stat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.stat-label {
  font-size: 13px;
  color: var(--muted);
}

.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
}

.stat-value {
  margin-top: 10px;
  font-size: 26px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.2;
  letter-spacing: 0.2px;
}

.stat-suffix {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--muted);
}

.stat-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #93a1b8;
}
</style>
