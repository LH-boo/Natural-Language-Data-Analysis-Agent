<template>
  <div class="chart-panel" :style="{ height }">
    <div ref="chartEl" class="chart-canvas"></div>
    <div v-if="!hasOption" class="chart-empty">
      <el-icon :size="30"><PieChart /></el-icon>
      <span>{{ emptyText }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { PieChart } from '@element-plus/icons-vue'

const props = defineProps({
  option: {
    type: Object,
    default: null
  },
  height: {
    type: String,
    default: '320px'
  },
  emptyText: {
    type: String,
    default: '暂无图表数据'
  }
})

const chartEl = ref(null)
const hasOption = computed(() => Boolean(props.option && Object.keys(props.option).length))
let chart = null
let observer = null

function renderChart() {
  if (!chartEl.value) return
  if (!hasOption.value) {
    chart?.clear()
    return
  }
  if (!chart) {
    chart = echarts.init(chartEl.value)
  }
  chart.setOption(props.option, true)
  chart.resize()
}

function resizeChart() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  renderChart()
  if (typeof ResizeObserver !== 'undefined' && chartEl.value) {
    observer = new ResizeObserver(() => resizeChart())
    observer.observe(chartEl.value)
  }
})

watch(
  () => props.option,
  async () => {
    await nextTick()
    renderChart()
  },
  { deep: true }
)

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart-panel {
  position: relative;
  width: 100%;
  min-height: 200px;
}

.chart-canvas {
  width: 100%;
  height: 100%;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #93a1b8;
  font-size: 13px;
  background: linear-gradient(180deg, #fbfdff, #f6f9ff);
  border-radius: 12px;
}
</style>
