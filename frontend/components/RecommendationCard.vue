<template>
  <div
    class="bg-white rounded-lg border p-5 transition-all duration-200"
    :class="cardClasses"
  >
    <!-- Default summary view -->
    <div class="flex items-start justify-between gap-4">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold"
            :class="priorityClasses"
          >
            {{ recommendation.priority.toUpperCase() }}
          </span>
          <span class="text-sm font-semibold text-gray-900 truncate">
            {{ recommendation.criterion_name }}
          </span>
          <span class="text-xs text-gray-400">
            {{ recommendation.page_url || 'Site-wide' }}
          </span>
        </div>

        <p class="mt-2 text-sm" :class="summaryTextClasses">
          {{ recommendation.summary }}
        </p>

        <div class="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span>
            Impact: <span class="font-medium text-gray-700">{{ recommendation.impact_label }}</span>
          </span>
          <span>
            Gap: <span class="font-medium font-mono text-gray-700">{{ recommendation.gap_score }}pts</span>
          </span>
          <span>
            Competitor avg: <span class="font-medium font-mono text-gray-700">{{ recommendation.competitor_avg ?? 'N/A' }}</span>
          </span>
          <span>
            Your score: <span class="font-medium font-mono text-gray-700">{{ recommendation.user_score }}</span>
          </span>
        </div>
      </div>

      <!-- Action buttons -->
      <div class="flex items-center gap-2 flex-shrink-0">
        <template v-if="recommendation.status === 'open'">
          <button
            @click="$emit('update-status', { id: recommendation.id, status: 'done' })"
            class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md border border-green-300 text-green-700 hover:bg-green-50 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-1"
          >
            <CheckIcon class="w-3.5 h-3.5" />
            Done
          </button>
          <button
            @click="$emit('update-status', { id: recommendation.id, status: 'dismissed' })"
            class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-1"
          >
            <XMarkIcon class="w-3.5 h-3.5" />
            Dismiss
          </button>
        </template>
        <template v-else>
          <span
            class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-md"
            :class="recommendation.status === 'done' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
          >
            <CheckIcon v-if="recommendation.status === 'done'" class="w-3.5 h-3.5" />
            <XMarkIcon v-else class="w-3.5 h-3.5" />
            {{ recommendation.status === 'done' ? 'Done' : 'Dismissed' }}
          </span>
          <button
            @click="$emit('update-status', { id: recommendation.id, status: 'open' })"
            class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-500 hover:bg-gray-50 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-1"
          >
            <ArrowUturnLeftIcon class="w-3.5 h-3.5" />
            Undo
          </button>
        </template>
      </div>
    </div>

    <!-- Toggle expand button -->
    <div class="mt-3 border-t border-gray-100 pt-2">
      <button
        @click="expanded = !expanded"
        class="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 rounded px-1 py-0.5"
      >
        {{ expanded ? 'Hide Steps' : 'See Steps' }}
        <ChevronDownIcon
          class="w-3.5 h-3.5 transition-transform duration-200"
          :class="{ 'rotate-180': expanded }"
        />
      </button>
    </div>

    <!-- Expanded detail view -->
    <div v-show="expanded" class="mt-3 space-y-4">
      <!-- Action steps -->
      <div>
        <h4 class="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Action Steps</h4>
        <ol class="list-decimal list-inside space-y-1.5 text-sm text-gray-700">
          <li v-for="(step, i) in recommendation.action_steps" :key="i" class="leading-relaxed">
            {{ step }}
          </li>
        </ol>
      </div>

      <!-- Code snippet -->
      <div v-if="recommendation.code_snippet">
        <h4 class="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Code Example</h4>
        <pre class="bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-sm overflow-x-auto whitespace-pre-wrap">{{ recommendation.code_snippet }}</pre>
      </div>

      <!-- Evidence source -->
      <p class="text-xs text-gray-500 italic">
        Source: {{ recommendation.evidence_source }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  CheckIcon,
  XMarkIcon,
  ChevronDownIcon,
  ArrowUturnLeftIcon,
} from '@heroicons/vue/24/outline'

interface Recommendation {
  id: string
  audit_id: string
  page_url: string | null
  criterion_id: string
  criterion_name: string
  category: string
  priority: string
  impact_label: string
  impact_pct: number | null
  user_score: number
  competitor_avg: number | null
  gap_score: number
  summary: string
  action_steps: string[]
  code_snippet: string | null
  evidence_source: string
  recommendation_hash: string
  status: string
}

const props = defineProps<{
  recommendation: Recommendation
}>()

defineEmits<{
  'update-status': [payload: { id: string; status: 'done' | 'dismissed' | 'open' }]
}>()

const expanded = ref(false)

const priorityClasses = computed(() => {
  switch (props.recommendation.priority) {
    case 'high':
      return 'bg-red-100 text-red-700'
    case 'medium':
      return 'bg-amber-100 text-amber-700'
    case 'low':
      return 'bg-blue-100 text-blue-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
})

const cardClasses = computed(() => {
  switch (props.recommendation.status) {
    case 'done':
      return 'bg-green-50 border-green-200'
    case 'dismissed':
      return 'bg-gray-50 border-gray-200 opacity-60'
    default:
      return 'border-gray-200'
  }
})

const summaryTextClasses = computed(() => {
  switch (props.recommendation.status) {
    case 'done':
      return 'text-gray-500 line-through'
    case 'dismissed':
      return 'text-gray-400'
    default:
      return 'text-gray-700'
  }
})
</script>
