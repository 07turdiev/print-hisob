<script setup lang="ts">
import { useEmployeesPage } from '../composables/useEmployeesPage'
import { useOverrideActions } from '../composables/useOverrideActions'
import { usePeriodStore } from '../stores/period'
import AppIcon from '../components/AppIcon.vue'
import AdSyncBanner from '../components/AdSyncBanner.vue'
import DepartmentFilter from '../components/DepartmentFilter.vue'
import EmployeeQuotaTable from '../components/EmployeeQuotaTable.vue'
import CsvDownloadButton from '../components/CsvDownloadButton.vue'
import LinkEmployeeDialog from '../components/LinkEmployeeDialog.vue'

const periodStore = usePeriodStore()
const {
  rows,
  search,
  activeFilter,
  departmentOptions,
  directoryOptions,
  defaultQuota,
  adSyncStatus,
  loading,
  error,
  saveQuota,
  saveOverride,
} = useEmployeesPage()

const { busyLogin, linkTarget, actionError, toggleBlock, startLink, cancelLink, confirmLink, unlink } =
  useOverrideActions(saveOverride)

function handleSave(login: string, allocatedPages: number) {
  saveQuota(login, allocatedPages).catch(() => {
    // EmployeeQuotaTable tahrir holatini o'zi tiklaydi; bu yerda xato halokatli emas.
  })
}
</script>

<template>
  <div class="page">
    <p v-if="error" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ error }}</span>
    </p>

    <AdSyncBanner :status="adSyncStatus" />

    <div class="filter-bar">
      <label class="field field--grow">
        <span>Qidiruv</span>
        <span class="search-box">
          <AppIcon name="search" :size="15" />
          <input v-model="search" type="text" placeholder="Login yoki F.I.SH. bo'yicha qidirish" />
        </span>
      </label>

      <DepartmentFilter :department-options="departmentOptions" />

      <label class="field">
        <span>Holat</span>
        <select v-model="activeFilter">
          <option value="">Barchasi</option>
          <option value="active">Faol</option>
          <option value="inactive">Ketgan</option>
        </select>
      </label>
    </div>

    <p class="alert alert--info">
      <span class="alert__icon"><AppIcon name="info" :size="16" /></span>
      <span>
        Kvota faqat tanlangan davr uchun saqlanadi. Kvotasi belgilanmagan xodimlarga standart
        <strong>{{ defaultQuota }}</strong> varaq qo'llaniladi. Kvotani o'zgartirish uchun jadvaldagi
        qiymat ustiga bosing.
      </span>
    </p>

    <p v-if="actionError" class="alert alert--danger">
      <span class="alert__icon"><AppIcon name="warning" :size="16" /></span>
      <span>{{ actionError }}</span>
    </p>

    <EmployeeQuotaTable
      :employees="rows"
      title="Xodimlar va kvotalar ro'yxati"
      :busy-login="busyLogin"
      @save="handleSave"
      @toggle-block="toggleBlock"
      @link="startLink"
      @unlink="unlink"
    >
      <template #actions>
        <CsvDownloadButton
          :period-type="periodStore.periodType"
          :year="periodStore.year"
          :period-no="periodStore.periodNo"
          :department="periodStore.department"
        />
      </template>
    </EmployeeQuotaTable>

    <LinkEmployeeDialog
      :employee="linkTarget"
      :options="directoryOptions"
      :saving="busyLogin !== null"
      :error="actionError"
      @select="confirmLink"
      @close="cancelLink"
    />

    <p v-if="loading" class="loading-pill">Yuklanmoqda...</p>
  </div>
</template>
