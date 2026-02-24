<template>
  <div
    class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-semibold mb-1"
    :class="delta > 0 ? 'bg-green-100 text-green-700' : delta < 0 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'"
    data-testid="delta-badge"
  >
    <ArrowTrendingUpIcon v-if="delta > 0" class="w-3.5 h-3.5" />
    <ArrowTrendingDownIcon v-else-if="delta < 0" class="w-3.5 h-3.5" />
    <span>{{ delta > 0 ? '+' : '' }}{{ delta }}</span>
  </div>
</template>

<script setup lang="ts">
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/vue/24/solid'

defineProps<{
  delta: number
}>()
</script>
