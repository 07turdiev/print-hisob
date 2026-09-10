<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { useChartTheme } from '../utils/chartTheme'
import AppIcon from './AppIcon.vue'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = withDefaults(
  defineProps<{
    title: string
    items: { name: string; value: number }[]
    valueLabel: string
    icon?: string
  }>(),
  { icon: 'chart' },
)

const chartTheme = useChartTheme()

const option = computed(() => {
  const t = chartTheme.value
  return {
    color: [t.palette[0]],
    textStyle: t.textStyle,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...t.tooltip },
    grid: { left: 8, right: 32, top: 14, bottom: 4, containLabel: true },
    xAxis: {
      type: 'value',
      name: props.valueLabel,
      nameTextStyle: { color: t.colors.textMuted, fontSize: 11 },
      axisLabel: { color: t.colors.textMuted, fontSize: 11 },
      axisLine: { show: false },
      splitLine: t.splitLine,
    },
    yAxis: {
      type: 'category',
      // Eng katta qiymat tepada tursin
      inverse: true,
      data: props.items.map((i) => i.name),
      axisLabel: { width: 190, overflow: 'truncate', color: t.colors.text, fontSize: 11 },
      axisLine: t.axisLine,
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: props.items.map((i) => i.value),
        barMaxWidth: 16,
        itemStyle: { color: t.palette[0], borderRadius: [0, 2, 2, 0] },
        label: { show: true, position: 'right', color: t.colors.textMuted, fontSize: 11 },
      },
    ],
  }
})

const height = computed(() => `${Math.max(180, props.items.length * 30 + 46)}px`)
</script>

<template>
  <section class="panel">
    <header class="panel__head">
      <h2 class="panel__title">
        <span class="panel__title-icon"><AppIcon :name="icon" :size="16" /></span>
        {{ title }}
      </h2>
    </header>

    <div class="panel__body">
      <VChart v-if="items.length" class="chart" :style="{ height }" :option="option" autoresize />
      <div v-else class="empty-state">
        <span class="empty-state__icon"><AppIcon name="chart" :size="20" /></span>
        Ma'lumot topilmadi
      </div>
    </div>
  </section>
</template>

<style scoped>
.chart {
  width: 100%;
}
</style>
