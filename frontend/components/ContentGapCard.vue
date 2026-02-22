<template>
  <div class="border border-amber-200 bg-amber-50 rounded-lg p-4">
    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div class="flex-1 min-w-0">
        <h4 class="text-sm font-semibold text-gray-900">{{ gap.query_text }}</h4>
        <p class="text-xs text-gray-500 mt-1">
          Mentioned: <span class="text-gray-600">{{ gap.competitors_mentioned.join(', ') || 'None' }}</span>
        </p>
      </div>
      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-700 flex-shrink-0">
        Missing
      </span>
    </div>

    <!-- Brief toggle -->
    <div class="mt-3">
      <button
        @click="showBrief = !showBrief"
        class="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1 py-0.5"
      >
        {{ showBrief ? 'Hide Brief' : 'Show Brief' }}
      </button>
    </div>

    <!-- Expandable brief section -->
    <div v-show="showBrief" class="mt-3 border-t border-amber-200 pt-3">
      <p class="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Suggested Content</p>

      <p class="text-sm font-medium text-gray-900 mb-2">
        Title: {{ gap.brief.title }}
      </p>

      <ul class="list-disc list-inside space-y-1 text-sm text-gray-700">
        <li v-for="(point, i) in gap.brief.key_points" :key="i">
          {{ point }}
        </li>
      </ul>

      <div v-if="gap.brief.target_queries && gap.brief.target_queries.length > 0" class="mt-2">
        <p class="text-xs text-gray-500">
          Target queries: {{ gap.brief.target_queries.join(', ') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface ContentGap {
  query_id: string
  query_text: string
  competitors_mentioned: string[]
  brief: {
    title: string
    key_points: string[]
    target_queries: string[]
  }
}

defineProps<{
  gap: ContentGap
}>()

const showBrief = ref(false)
</script>
