<template>
  <div class="space-y-6">
    <!-- Score Hero Section -->
    <div class="bg-white rounded-lg border border-gray-200 p-8 text-center">
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
    <div v-if="perEngineScores.length > 0" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
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

interface AuditData {
  id: string
  url: string
  domain: string
  status: string
  visibility_score: VisibilityScore | null
  queries: AuditQuery[]
  dispatch_summary: DispatchSummary | null
}

const props = defineProps<{
  audit: AuditData
}>()

const ENGINE_DISPLAY_NAMES: Record<string, string> = {
  openai: 'ChatGPT',
  anthropic: 'Claude',
  perplexity: 'Perplexity',
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
</script>
