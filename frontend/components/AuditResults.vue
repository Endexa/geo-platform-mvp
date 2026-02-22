<template>
  <div class="space-y-6">
    <!-- Dual Score Hero Section -->
    <OptimizationScore
      v-if="audit.optimization_score"
      :optimization="audit.optimization_score"
      :visibility="audit.visibility_score"
    />

    <!-- Fallback: Visibility-only hero (when no optimization score yet) -->
    <div v-else class="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <p class="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">AI Visibility Score</p>
      <div
        class="inline-flex items-center justify-center w-28 h-28 rounded-full border-4 mb-3"
        :class="scoreColor.border"
      >
        <span class="text-4xl font-bold" :class="scoreColor.text">
          {{ overallScore }}
        </span>
      </div>
      <p class="text-gray-600">{{ audit.domain }}</p>
    </div>

    <!-- Per-Engine Breakdown -->
    <div v-if="perEngineScores.length > 0" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div
        v-for="engine in perEngineScores"
        :key="engine.key"
        class="bg-white rounded-lg border border-gray-200 p-6 text-center"
      >
        <p class="text-sm font-medium text-gray-500 mb-1">{{ engine.displayName }}</p>
        <p class="text-3xl font-bold" :class="getScoreColor(engine.score).text">
          {{ engine.score }}
        </p>
        <p class="text-xs text-gray-400 mt-1">/ 100</p>
      </div>
    </div>

    <!-- Summary Stats Row -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p class="text-2xl font-bold text-gray-900">{{ audit.visibility_score?.mention_count ?? 0 }}</p>
        <p class="text-xs text-gray-500 mt-1">Brand Mentions</p>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p class="text-2xl font-bold text-gray-900">{{ mentionRateFormatted }}</p>
        <p class="text-xs text-gray-500 mt-1">Mention Rate</p>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p class="text-2xl font-bold text-gray-900">{{ audit.dispatch_summary?.total_queries ?? 0 }}</p>
        <p class="text-xs text-gray-500 mt-1">Queries Sent</p>
      </div>
      <div class="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p class="text-2xl font-bold text-gray-900">{{ audit.dispatch_summary?.total_responses ?? 0 }}</p>
        <p class="text-xs text-gray-500 mt-1">Responses Received</p>
      </div>
    </div>

    <!-- Category Breakdown -->
    <CategoryBreakdown
      v-if="audit.optimization_score"
      :optimization="audit.optimization_score"
      :selected-category="selectedCategory"
      @select="onCategorySelect"
    />

    <!-- Criterion Drilldown -->
    <CriterionDrilldown
      v-if="selectedCategory && scoredPages.length > 0"
      :page-scores="scoredPages"
      :selected-category="selectedCategory"
      @close="selectedCategory = null"
    />

    <!-- Discovered but not scored pages -->
    <div v-if="unscoredPages.length > 0" class="bg-white rounded-lg border border-gray-200 p-6">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">
        Discovered but not scored ({{ unscoredPages.length }} pages)
      </h3>
      <p class="text-xs text-gray-500 mb-3">
        These pages were discovered during the crawl but not scored due to the 25-page cap.
      </p>
      <ul class="space-y-1">
        <li v-for="page in unscoredPages" :key="page.page_url" class="text-sm text-gray-600 truncate" :title="page.page_url">
          {{ page.page_url }}
        </li>
      </ul>
    </div>

    <!-- Query List -->
    <div class="space-y-3">
      <h3 class="text-lg font-semibold text-gray-900">Queries ({{ sortedQueries.length }})</h3>
      <QueryDetail
        v-for="query in sortedQueries"
        :key="query.id"
        :query="query"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
interface BrandMention {
  id: string
  matched_text: string
  match_type: string
  confidence: number
  char_offset: number
  context_quote: string
}

interface EngineResponseData {
  id: string
  engine: string
  model_version: string
  response_text: string
  error_message: string | null
  mentions: BrandMention[]
}

interface AuditQuery {
  id: string
  category: string
  query_text: string
  sort_order: number
  engine_responses: EngineResponseData[]
}

interface VisibilityScore {
  overall_score: number
  per_engine_scores: Record<string, number>
  mention_count: number
  query_mention_rate: number
  algorithm_version: string
}

interface DispatchSummary {
  total_queries: number
  total_responses: number
  total_failures: number
  engines_used: string[]
}

interface OptimizationScore {
  overall_score: number
  crawlability_avg: number
  content_structure_avg: number
  structured_data_avg: number
  authority_avg: number
  pages_scored: number
  pages_discovered: number
}

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

interface PageScoreData {
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

interface AuditData {
  id: string
  url: string
  domain: string
  status: string
  visibility_score: VisibilityScore | null
  queries: AuditQuery[]
  dispatch_summary: DispatchSummary | null
  optimization_score: OptimizationScore | null
  page_scores: PageScoreData[]
}

const props = defineProps<{
  audit: AuditData
}>()

const selectedCategory = ref<string | null>(null)

const ENGINE_DISPLAY_NAMES: Record<string, string> = {
  openai: 'ChatGPT',
  anthropic: 'Claude',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
}

const overallScore = computed(() => props.audit.visibility_score?.overall_score ?? 0)

const mentionRateFormatted = computed(() => {
  const rate = props.audit.visibility_score?.query_mention_rate ?? 0
  return `${Math.round(rate)}%`
})

function getScoreColor(score: number) {
  if (score >= 70) return { text: 'text-green-600', border: 'border-green-500' }
  if (score >= 40) return { text: 'text-yellow-600', border: 'border-yellow-500' }
  return { text: 'text-red-600', border: 'border-red-500' }
}

const scoreColor = computed(() => getScoreColor(overallScore.value))

const perEngineScores = computed(() => {
  const scores = props.audit.visibility_score?.per_engine_scores
  if (!scores) return []
  return Object.entries(scores).map(([key, score]) => ({
    key,
    displayName: ENGINE_DISPLAY_NAMES[key] || key,
    score,
  }))
})

const sortedQueries = computed(() => {
  return [...props.audit.queries].sort((a, b) => a.sort_order - b.sort_order)
})

const scoredPages = computed(() => {
  return (props.audit.page_scores ?? []).filter(ps => ps.was_scored)
})

const unscoredPages = computed(() => {
  return (props.audit.page_scores ?? []).filter(ps => !ps.was_scored)
})

function onCategorySelect(category: string) {
  selectedCategory.value = selectedCategory.value === category ? null : category
}
</script>
