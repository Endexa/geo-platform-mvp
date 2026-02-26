<template>
  <div class="flex items-center gap-3">
    <!-- PDF Export -->
    <button
      :disabled="exportingPdf"
      class="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-primary-800 text-white hover:bg-primary-900 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2 transition-colors duration-200"
      @click="downloadPdf"
    >
      <ArrowDownTrayIcon class="w-4 h-4 mr-1.5" />
      <template v-if="exportingPdf">Generating...</template>
      <template v-else>Export PDF</template>
    </button>

    <!-- CSV Export -->
    <button
      :disabled="exportingCsv"
      class="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2 transition-colors duration-200"
      @click="downloadCsv"
    >
      <ArrowDownTrayIcon class="w-4 h-4 mr-1.5" />
      <template v-if="exportingCsv">Generating...</template>
      <template v-else>Export CSV</template>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ArrowDownTrayIcon } from '@heroicons/vue/24/outline'

const props = defineProps<{
  auditId: string
  domain: string
}>()

const config = useRuntimeConfig()
const exportingPdf = ref(false)
const exportingCsv = ref(false)

function getToken(): string | null {
  if (import.meta.server) return null
  const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

async function downloadPdf() {
  exportingPdf.value = true
  try {
    const token = getToken()
    const blob = await $fetch<Blob>(
      `/api/v1/dashboard/${props.auditId}/export/pdf`,
      {
        baseURL: config.public.apiUrl,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        responseType: 'blob',
      },
    )

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `geo-audit-${props.domain}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('PDF export failed:', e)
  } finally {
    exportingPdf.value = false
  }
}

async function downloadCsv() {
  exportingCsv.value = true
  try {
    const token = getToken()
    const blob = await $fetch<Blob>(
      `/api/v1/dashboard/${props.auditId}/export/csv`,
      {
        baseURL: config.public.apiUrl,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        responseType: 'blob',
      },
    )

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `geo-audit-${props.domain}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('CSV export failed:', e)
  } finally {
    exportingCsv.value = false
  }
}
</script>
