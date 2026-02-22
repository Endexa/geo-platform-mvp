<template>
  <div class="bg-white rounded-lg border border-gray-200 p-5">
    <!-- Progress bar -->
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-semibold text-gray-900">Recommendation Progress</span>
      <span class="text-sm font-medium text-gray-600">
        {{ progress.done + progress.dismissed }}/{{ progress.total }} addressed
      </span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
      <div
        class="bg-green-500 h-2.5 rounded-full transition-all duration-300"
        :style="{ width: progressPercent + '%' }"
      />
    </div>

    <!-- Per-priority remaining counts -->
    <div v-if="byPriority" class="mt-2 flex items-center gap-4 text-xs text-gray-500">
      <span>
        <span class="inline-block w-2 h-2 rounded-full bg-red-400 mr-1" />
        High: {{ byPriority.high }} remaining
      </span>
      <span>
        <span class="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1" />
        Medium: {{ byPriority.medium }} remaining
      </span>
      <span>
        <span class="inline-block w-2 h-2 rounded-full bg-blue-400 mr-1" />
        Low: {{ byPriority.low }} remaining
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface ProgressData {
  done: number
  dismissed: number
  open: number
  total: number
}

interface PriorityData {
  high: number
  medium: number
  low: number
}

const props = defineProps<{
  progress: ProgressData
  byPriority?: PriorityData
}>()

const progressPercent = computed(() => {
  if (props.progress.total === 0) return 0
  return Math.round(
    ((props.progress.done + props.progress.dismissed) / props.progress.total) * 100
  )
})
</script>
