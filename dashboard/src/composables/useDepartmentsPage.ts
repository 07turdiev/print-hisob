import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ApiError, getDepartmentStats } from '../api/client'
import type { DepartmentStat } from '../api/types'
import { usePeriodStore } from '../stores/period'

export function useDepartmentsPage() {
  const periodStore = usePeriodStore()
  const { periodType, year, periodNo } = storeToRefs(periodStore)

  const departments = ref<DepartmentStat[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function reload() {
    loading.value = true
    error.value = null
    try {
      departments.value = await getDepartmentStats({
        periodType: periodType.value,
        year: year.value,
        periodNo: periodNo.value,
      })
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Ma'lumotlarni yuklab bo'lmadi"
    } finally {
      loading.value = false
    }
  }

  watch([periodType, year, periodNo], reload, { immediate: true })

  const sortedDepartments = computed(() => [...departments.value].sort((a, b) => b.pages - a.pages))

  const departmentChartItems = computed(() => sortedDepartments.value.map((d) => ({ name: d.name, value: d.pages })))

  return {
    departments: sortedDepartments,
    departmentChartItems,
    loading,
    error,
  }
}
