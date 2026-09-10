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
import { useChartTheme, withAlpha } from '../utils/chartTheme'
import AppIcon from './AppIcon.vue'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
])

const props = withDefaults(defineProps<{ points: TimeseriesPoint[]; title?: string }>(), {
  title: 'Kunlik dinamika',
})

const chartTheme = useChartTheme()

const option = computed(() => {
  const t = chartTheme.value
  const lineColor = t.palette[0]
  const barColor = t.palette[1]
  return {
    color: [lineColor, barColor],
    textStyle: t.textStyle,
    tooltip: { trigger: 'axis', ...t.tooltip },
    legend: {
      data: ['Varaqlar', 'Buyurtmalar'],
      top: 0,
      right: 0,
      itemWidth: 12,
      itemHeight: 8,
      textStyle: { color: t.colors.textMuted, fontSize: 11 },
    },
    grid: { left: 46, right: 20, top: 34, bottom: 42 },
    xAxis: {
      type: 'category',
      data: props.points.map((p) => p.date),
      axisLabel: { hideOverlap: true, color: t.colors.textMuted, fontSize: 11 },
      axisLine: t.axisLine,
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Varaq',
        nameTextStyle: { color: t.colors.textMuted, fontSize: 11 },
        axisLabel: { color: t.colors.textMuted, fontSize: 11 },
        axisLine: { show: false },
        splitLine: t.splitLine,
      },
      {
        type: 'value',
        name: 'Ish',
        nameTextStyle: { color: t.colors.textMuted, fontSize: 11 },
        splitLine: { show: false },
        axisLabel: { color: t.colors.textMuted, fontSize: 11 },
        axisLine: { show: false },
      },
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 14, bottom: 6 }],
    series: [
      {
        name: 'Varaqlar',
        type: 'line',
        smooth: 0.25,
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: lineColor },
        itemStyle: { color: lineColor },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: withAlpha(lineColor, 0.26) },
              { offset: 1, color: withAlpha(lineColor, 0) },
            ],
          },
        },
        data: props.points.map((p) => p.pages),
      },
      {
        name: 'Buyurtmalar',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 12,
        itemStyle: { color: withAlpha(barColor, 0.75), borderRadius: [2, 2, 0, 0] },
        data: props.points.map((p) => p.jobs),
      },
    ],
  }
})
</script>

<template>
  <section class="panel">
    <header class="panel__head">
      <h2 class="panel__title">
        <span class="panel__title-icon"><AppIcon name="chart" :size="16" /></span>
        {{ title }}
      </h2>
    </header>

    <div class="panel__body">
      <VChart v-if="points.length" class="chart" :option="option" autoresize />
      <div v-else class="empty-state">
        <span class="empty-state__icon"><AppIcon name="chart" :size="20" /></span>
        Tanlangan davr uchun kunlik ma'lumot yo'q
      </div>
    </div>
  </section>
</template>

<style scoped>
.chart {
  height: 300px;
  width: 100%;
}
</style>
