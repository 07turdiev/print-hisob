<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import type { TimeseriesPoint } from '../api/types'
import { useChartTheme } from '../utils/chartTheme'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
])

const props = defineProps<{ points: TimeseriesPoint[] }>()
const chartTheme = useChartTheme()

const option = computed(() => {
  const t = chartTheme.value
  const lineColor = t.palette[0]
  const barColor = t.palette[3]
  return {
    color: [lineColor, barColor],
    textStyle: t.textStyle,
    tooltip: { trigger: 'axis', ...t.tooltip },
    legend: { data: ['Varaqlar', 'Buyurtmalar'], top: 0, textStyle: { color: t.colors.textMuted } },
    grid: { left: 48, right: 16, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: props.points.map((p) => p.date),
      axisLabel: { hideOverlap: true, color: t.colors.textMuted },
      axisLine: t.axisLine,
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Varaqlar',
        axisLabel: { color: t.colors.textMuted },
        axisLine: { show: false },
        splitLine: t.splitLine,
      },
      {
        type: 'value',
        name: 'Buyurtmalar',
        splitLine: { show: false },
        axisLabel: { color: t.colors.textMuted },
        axisLine: { show: false },
      },
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
    series: [
      {
        name: 'Varaqlar',
        type: 'line',
        smooth: 0.3,
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2.5, color: lineColor },
        itemStyle: { color: lineColor },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(99, 102, 241, 0.30)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0)' },
            ],
          },
        },
        data: props.points.map((p) => p.pages),
      },
      {
        name: 'Buyurtmalar',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 14,
        itemStyle: { color: barColor, borderRadius: [4, 4, 0, 0] },
        data: props.points.map((p) => p.jobs),
      },
    ],
  }
})
</script>

<template>
  <div class="card">
    <h2>Kunlik dinamika</h2>
    <VChart class="chart" :option="option" autoresize />
  </div>
</template>

<style scoped>
.chart {
  height: 320px;
  width: 100%;
}
</style>
