<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { useChartTheme } from '../utils/chartTheme'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps<{
  title: string
  items: { name: string; value: number }[]
  valueLabel: string
}>()

const chartTheme = useChartTheme()

const option = computed(() => {
  const t = chartTheme.value
  return {
    color: [t.palette[0]],
    textStyle: t.textStyle,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...t.tooltip },
    grid: { left: 12, right: 24, top: 20, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      name: props.valueLabel,
      axisLabel: { color: t.colors.textMuted },
      axisLine: { show: false },
      splitLine: t.splitLine,
    },
    yAxis: {
      type: 'category',
      data: props.items.map((i) => i.name),
      axisLabel: { width: 140, overflow: 'truncate', color: t.colors.textMuted },
      axisLine: t.axisLine,
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: props.items.map((i) => i.value),
        barMaxWidth: 22,
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: t.palette[0] },
              { offset: 1, color: t.palette[1] },
            ],
          },
        },
        label: { show: true, position: 'right', color: t.colors.text },
      },
    ],
  }
})

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
