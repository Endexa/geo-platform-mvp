<template>
  <div class="border border-gray-200 rounded-lg p-4 bg-white">
    <!-- Top row: category pill + criterion badge + status -->
    <div class="flex items-center flex-wrap gap-2 mb-2">
      <span :class="categoryPillClass">{{ rec.category.replace('_', ' ') }}</span>
      <span v-if="rec.criterion_id" class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono bg-gray-100 text-gray-600">
        {{ rec.criterion_id }}
      </span>
      <div class="ml-auto">
        <select
          :value="rec.status"
          @change="emitStatusChange($event)"
          class="text-xs border border-gray-200 rounded px-2 py-0.5 text-gray-600 bg-white cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition"
        >
          <option value="open">Open</option>
          <option value="done">Done</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>
    </div>

    <!-- Finding -->
    <p class="text-sm font-semibold text-gray-900 mb-1">{{ rec.finding }}</p>

    <!-- File path -->
    <div v-if="rec.file_path" class="flex items-center gap-1 mb-2">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5 text-gray-400 flex-shrink-0">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
      </svg>
      <span class="text-sm font-mono text-gray-600 truncate">{{ rec.file_path }}</span>
    </div>

    <!-- Suggestion -->
    <p class="text-sm text-gray-700 mb-2">{{ rec.suggestion }}</p>

    <!-- Code snippet -->
    <div v-if="rec.code_snippet" class="mb-2">
      <pre class="bg-gray-50 border border-gray-200 rounded p-2 text-xs font-mono max-h-32 overflow-y-auto whitespace-pre-wrap break-all"><code>{{ rec.code_snippet }}</code></pre>
    </div>

    <!-- Evidence (collapsible) -->
    <div v-if="rec.evidence">
      <button
        @click="showEvidence = !showEvidence"
        class="text-xs text-gray-400 hover:text-gray-600 cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500 rounded transition-colors duration-150"
      >
        {{ showEvidence ? 'Hide evidence' : 'Show evidence' }}
      </button>
      <p v-if="showEvidence" class="mt-1 text-xs text-gray-500 italic">{{ rec.evidence }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface CodeRecommendationResponse {
  id: string
  code_analysis_id: string
  criterion_id: string | null
  category: string
  severity: string
  finding: string
  file_path: string | null
  suggestion: string
  code_snippet: string | null
  evidence: string | null
  status: string
  created_at: string
}

const props = defineProps<{
  rec: CodeRecommendationResponse
}>()

const emit = defineEmits<{
  (e: 'status-change', payload: { id: string; status: string }): void
}>()

const showEvidence = ref(false)

const CATEGORY_COLORS: Record<string, string> = {
  crawlability: 'bg-blue-50 text-blue-700 border border-blue-200',
  content_structure: 'bg-green-50 text-green-700 border border-green-200',
  structured_data: 'bg-purple-50 text-purple-700 border border-purple-200',
  authority: 'bg-amber-50 text-amber-700 border border-amber-200',
}

const categoryPillClass = computed(() => {
  const base = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize'
  const color = CATEGORY_COLORS[props.rec.category] || 'bg-gray-100 text-gray-600 border border-gray-200'
  return `${base} ${color}`
})

function emitStatusChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('status-change', { id: props.rec.id, status: target.value })
}
</script>
