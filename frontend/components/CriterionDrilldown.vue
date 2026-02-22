<template>
  <div v-if="selectedCategory" class="bg-white rounded-lg border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">
        {{ categoryLabel }} Criteria
      </h3>
      <button
        class="text-sm text-gray-500 hover:text-gray-700 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 rounded px-2 py-1 transition-colors duration-200"
        @click="$emit('close')"
      >
        Close
      </button>
    </div>

    <!-- Group by page -->
    <div v-for="page in filteredPages" :key="page.page_url" class="mb-6 last:mb-0">
      <p class="text-sm font-medium text-gray-700 mb-2 truncate" :title="page.page_url">
        {{ page.page_title || page.page_url }}
      </p>

      <div class="space-y-2">
        <div
          v-for="criterion in page.criteria"
          :key="criterion.criterion_id"
          class="border border-gray-100 rounded-lg"
        >
          <!-- Criterion header -->
          <button
            class="w-full flex items-center gap-3 px-4 py-3 text-left cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 rounded-lg transition-colors duration-200 hover:bg-gray-50"
            @click="toggleCriterion(criterion.criterion_id)"
          >
            <!-- Status icon -->
            <component
              :is="getStatusIcon(criterion)"
              class="w-5 h-5 flex-shrink-0"
              :class="getStatusIconColor(criterion)"
            />

            <!-- Criterion name and summary -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800">{{ criterion.criterion_name }}</span>
                <span
                  v-if="!criterion.checked"
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500"
                >
                  Not checked
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-0.5 truncate">{{ criterion.human_summary }}</p>
            </div>

            <!-- Score -->
            <span class="text-sm font-bold font-mono min-w-[3ch] text-right" :class="getScoreText(criterion)">
              {{ criterion.checked ? criterion.score : '--' }}
            </span>
          </button>

          <!-- Expanded detail -->
          <div
            v-if="expandedCriteria.has(criterion.criterion_id)"
            class="px-4 pb-3 border-t border-gray-100"
          >
            <div class="mt-3 space-y-2">
              <div>
                <p class="text-xs font-medium text-gray-500 uppercase">Technical Detail</p>
                <p class="text-sm text-gray-700 mt-1">{{ criterion.technical_detail }}</p>
              </div>
              <div v-if="criterion.evidence">
                <p class="text-xs font-medium text-gray-500 uppercase">Evidence</p>
                <pre class="text-xs text-gray-600 mt-1 bg-gray-50 rounded p-2 overflow-x-auto">{{ formatEvidence(criterion.evidence) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p v-if="filteredPages.length === 0" class="text-sm text-gray-500 text-center py-4">
      No criteria data available for this category.
    </p>
  </div>
</template>

<script setup lang="ts">
import { CheckCircleIcon, XCircleIcon, MinusCircleIcon } from '@heroicons/vue/24/solid'

interface CriterionResult {
  criterion_id: string
  criterion_name: string
  category: string
  score: number
  max_score: number
  is_binary: boolean
  human_summary: string
  technical_detail: string
  evidence: Record<string, unknown> | null
  checked: boolean
}

interface PageScore {
  page_url: string
  page_title: string | null
  crawlability_score: number | null
  content_structure_score: number | null
  structured_data_score: number | null
  authority_score: number | null
  overall_page_score: number | null
  internal_link_count: number
  was_scored: boolean
  criterion_results: CriterionResult[]
}

const CATEGORY_LABELS: Record<string, string> = {
  crawlability: 'Crawlability',
  content_structure: 'Content Structure',
  structured_data: 'Structured Data',
  authority: 'Authority',
}

const props = defineProps<{
  pageScores: PageScore[]
  selectedCategory: string | null
}>()

defineEmits<{
  close: []
}>()

const expandedCriteria = ref(new Set<string>())

const categoryLabel = computed(() =>
  props.selectedCategory ? CATEGORY_LABELS[props.selectedCategory] || props.selectedCategory : ''
)

const filteredPages = computed(() => {
  if (!props.selectedCategory) return []

  return props.pageScores
    .filter(ps => ps.was_scored)
    .map(ps => ({
      page_url: ps.page_url,
      page_title: ps.page_title,
      criteria: ps.criterion_results
        .filter(cr => cr.category === props.selectedCategory)
        .sort((a, b) => a.criterion_id.localeCompare(b.criterion_id)),
    }))
    .filter(ps => ps.criteria.length > 0)
})

function toggleCriterion(id: string) {
  const next = new Set(expandedCriteria.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedCriteria.value = next
}

function getStatusIcon(criterion: CriterionResult) {
  if (!criterion.checked) return MinusCircleIcon
  if (criterion.score >= 60) return CheckCircleIcon
  return XCircleIcon
}

function getStatusIconColor(criterion: CriterionResult): string {
  if (!criterion.checked) return 'text-gray-400'
  if (criterion.score >= 60) return 'text-green-500'
  return 'text-red-500'
}

function getScoreText(criterion: CriterionResult): string {
  if (!criterion.checked) return 'text-gray-400'
  if (criterion.score >= 80) return 'text-emerald-600'
  if (criterion.score >= 60) return 'text-green-600'
  if (criterion.score >= 30) return 'text-yellow-600'
  return 'text-red-600'
}

function formatEvidence(evidence: Record<string, unknown>): string {
  return JSON.stringify(evidence, null, 2)
}
</script>
