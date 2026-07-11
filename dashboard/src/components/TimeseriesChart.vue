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

const option = computed(() => ({
  color: ['#2563eb', '#f2b84b'],
  textStyle: { fontFamily: 'inherit' },
  tooltip: { trigger: 'axis' },
  legend: { data: ['Varaqlar', 'Buyurtmalar'], top: 0 },
  grid: { left: 48, right: 16, top: 40, bottom: 40 },
  xAxis: {
    type: 'category',
    data: props.points.map((p) => p.date),
    axisLabel: { hideOverlap: true },
  },
  yAxis: [
    { type: 'value', name: 'Varaqlar' },
    { type: 'value', name: 'Buyurtmalar', splitLine: { show: false } },
  ],
  dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 4 }],
  series: [
    {
      name: 'Varaqlar',
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.12 },
      data: props.points.map((p) => p.pages),
    },
    {
      name: 'Buyurtmalar',
      type: 'bar',
      yAxisIndex: 1,
      barMaxWidth: 14,
      data: props.points.map((p) => p.jobs),
    },
  ],
}))
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
