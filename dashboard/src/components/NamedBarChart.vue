<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps<{
  title: string
  items: { name: string; value: number }[]
  valueLabel: string
}>()

const option = computed(() => ({
  color: ['#2563eb'],
  textStyle: { fontFamily: 'inherit' },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 12, right: 20, top: 20, bottom: 8, containLabel: true },
  xAxis: { type: 'value', name: props.valueLabel },
  yAxis: {
    type: 'category',
    data: props.items.map((i) => i.name),
    axisLabel: { width: 140, overflow: 'truncate' },
  },
  series: [
    {
      type: 'bar',
      data: props.items.map((i) => i.value),
      barMaxWidth: 22,
      label: { show: true, position: 'right' },
    },
  ],
}))

const height = computed(() => `${Math.max(200, props.items.length * 42 + 40)}px`)
</script>

<template>
  <div class="card">
    <h2>{{ title }}</h2>
    <VChart class="chart" :style="{ height }" :option="option" autoresize />
  </div>
</template>

<style scoped>
.chart {
  width: 100%;
}
</style>
