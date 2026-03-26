<template>
  <div class="space-y-3">
    <h4 class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Audits</h4>

    <!-- Active audit indicator -->
    <NuxtLink
      v-if="auditId && isRunning"
      to="/audit"
      class="flex items-center gap-2 px-3 py-2 bg-primary-50 border border-primary-200 rounded-lg text-sm cursor-pointer hover:bg-primary-100 transition-colors duration-200"
    >
      <span class="relative flex h-2.5 w-2.5 shrink-0">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary-600" />
      </span>
      <span class="truncate font-medium text-primary-700">{{ runningDomain }}</span>
    </NuxtLink>

    <!-- Recent history -->
    <div v-if="auditHistory.length > 0" class="space-y-1">
      <NuxtLink
        v-for="item in recentHistory"
        :key="item.id"
        :to="`/audit?id=${item.id}`"
        class="flex items-center justify-between px-3 py-2 rounded-lg text-sm cursor-pointer hover:bg-slate-100 transition-colors duration-200"
        :class="item.id === auditId ? 'bg-slate-100' : ''"
      >
        <span class="truncate text-slate-700">{{ item.domain || item.url }}</span>
        <span
          class="shrink-0 ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold"
          :class="statusBadgeClass(item.status)"
        >
          {{ statusLabel(item.status) }}
        </span>
      </NuxtLink>
    </div>

    <!-- Empty state -->
    <p v-else-if="!auditId" class="text-xs text-slate-400 px-3">
      No audits yet
    </p>

    <!-- View all link -->
    <NuxtLink
      v-if="auditHistory.length > 0"
      to="/dashboard"
      class="block px-3 text-xs text-slate-500 hover:text-primary-600 cursor-pointer transition-colors duration-200"
    >
      View all audits
    </NuxtLink>
  </div>
</template>

<script setup lang="ts">
const { auditId, audit, isRunning, auditHistory, loadHistory } = useAudit()

const recentHistory = computed(() => auditHistory.value.slice(0, 5))

const runningDomain = computed(() => {
  if (!audit.value) return 'Running...'
  return audit.value.domain || new URL(audit.value.url).hostname
})

function statusBadgeClass(s: string) {
  switch (s) {
    case 'completed': return 'bg-green-100 text-green-700'
    case 'failed': return 'bg-red-100 text-red-700'
    default: return 'bg-amber-100 text-amber-700'
  }
}

function statusLabel(s: string) {
  switch (s) {
    case 'completed': return 'Done'
    case 'failed': return 'Failed'
    default: return 'Running'
  }
}

onMounted(() => {
  if (auditHistory.value.length === 0) {
    loadHistory()
  }
})
</script>
