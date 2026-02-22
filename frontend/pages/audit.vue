<template>
  <div class="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">AI Brand Visibility Audit</h1>
        <p class="text-gray-600 mt-1">See how AI engines perceive and mention your brand</p>
      </div>

      <!-- Phase 1: URL Input (no audit started) -->
      <AuditForm v-if="!auditId" :loading="creating" @submit="startAudit" />

      <!-- Phase 2: Progress (audit running) -->
      <AuditProgress v-else-if="isRunning" :status="audit?.status ?? 'pending'" />

      <!-- Phase 3: Results (audit complete) -->
      <AuditResults v-else-if="isCompleted && audit" :audit="audit" />

      <!-- Competitor Preview (shown when audit completed and competitors discovered) -->
      <div v-if="isCompleted && competitorLeaderboard && competitorLeaderboard.competitors.length > 0" class="bg-white rounded-lg border border-gray-200">
        <div class="p-6 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold text-gray-900">Discovered Competitors</h3>
            <p class="text-sm text-gray-500 mt-1">Top brands mentioned by AI alongside yours</p>
          </div>
          <NuxtLink
            :to="`/competitors?audit_id=${auditId}`"
            class="text-sm text-primary-600 hover:text-primary-700 font-medium cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-2 py-1"
          >
            View All Competitors
          </NuxtLink>
        </div>
        <CompetitorLeaderboard
          :competitors="topCompetitors"
          :user-brand-name="competitorLeaderboard.user_brand_name"
        />
      </div>

      <!-- Source Citations from engine responses -->
      <SourceCitations
        v-if="isCompleted && audit && allEngineResponses.length > 0"
        :engine-responses="allEngineResponses"
      />

      <!-- Query Editor: visible when completed or pending -->
      <QueryEditor
        v-if="audit && auditId && (isCompleted || isPending)"
        :audit-id="auditId"
        :queries="audit.queries"
        @query-added="refreshAudit"
        @query-updated="refreshAudit"
        @query-deleted="refreshAudit"
      />

      <!-- Error State -->
      <div v-else-if="isFailed" class="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <p class="text-red-600 font-medium">Audit failed</p>
        <p class="text-gray-600 mt-2">{{ audit?.error_message || 'An unexpected error occurred.' }}</p>
        <button
          @click="resetAudit"
          class="mt-4 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 transition-colors duration-200"
        >
          Try Again
        </button>
      </div>

      <!-- API Error State -->
      <div v-if="apiError" class="bg-red-50 border border-red-200 rounded-lg p-4">
        <p class="text-sm text-red-700">{{ apiError }}</p>
      </div>
    </div>
</template>

<script setup lang="ts">
import { useIntervalFn } from '@vueuse/core'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

interface AuditDetail {
  id: string
  url: string
  domain: string
  status: string
  error_message: string | null
  visibility_score: {
    overall_score: number
    per_engine_scores: Record<string, number>
    mention_count: number
    query_mention_rate: number
    algorithm_version: string
  } | null
  optimization_score: {
    overall_score: number
    crawlability_avg: number
    content_structure_avg: number
    structured_data_avg: number
    authority_avg: number
    pages_scored: number
    pages_discovered: number
  } | null
  queries: Array<{
    id: string
    category: string
    query_text: string
    sort_order: number
    is_custom: boolean
    engine_responses: Array<{
      id: string
      engine: string
      model_version: string
      response_text: string
      error_message: string | null
      mentions: Array<{
        id: string
        matched_text: string
        match_type: string
        confidence: number
        char_offset: number
        context_quote: string
      }>
    }>
  }>
  dispatch_summary: {
    total_queries: number
    total_responses: number
    total_failures: number
    engines_used: string[]
  } | null
  page_scores: Array<{
    page_url: string
    page_title: string | null
    crawlability_score: number | null
    content_structure_score: number | null
    structured_data_score: number | null
    authority_score: number | null
    overall_page_score: number | null
    internal_link_count: number
    was_scored: boolean
    criterion_results: Array<{
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
    }>
  }>
}

interface CompetitorLeaderboardEntry {
  entity_name: string
  entity_type: string
  mention_count: number
  share_of_voice: number
  engines_mentioned_in: Record<string, number>
  queries_mentioned_in: string[]
  resolved_url: string | null
  is_crawled: boolean
  is_user_brand: boolean
  competitor_audit_id: string | null
}

interface CompetitorAuditSummary {
  id: string
  competitor_name: string
  competitor_url: string
  optimization_score: number | null
  crawlability_avg: number | null
  content_structure_avg: number | null
  structured_data_avg: number | null
  authority_avg: number | null
  pages_scored: number
  status: string
  created_at: string
}

interface LeaderboardResponse {
  audit_id: string
  user_brand_name: string
  total_entities: number
  competitors: CompetitorLeaderboardEntry[]
  competitor_audits: CompetitorAuditSummary[]
}

const auditId = ref<string | null>(null)
const audit = ref<AuditDetail | null>(null)
const creating = ref(false)
const apiError = ref('')
const competitorLeaderboard = ref<LeaderboardResponse | null>(null)

const isRunning = computed(() => {
  const s = audit.value?.status
  return s && !['completed', 'failed'].includes(s)
})

const isCompleted = computed(() => audit.value?.status === 'completed')
const isPending = computed(() => audit.value?.status === 'pending')
const isFailed = computed(() => audit.value?.status === 'failed')

// Top 5 competitors for preview on audit page
const topCompetitors = computed(() => {
  if (!competitorLeaderboard.value) return []
  return competitorLeaderboard.value.competitors.slice(0, 5)
})

// All engine responses across all queries for SourceCitations
const allEngineResponses = computed(() => {
  if (!audit.value) return []
  const responses: Array<{
    id: string
    engine: string
    model_version: string
    response_text: string
    error_message: string | null
    mentions: Array<{
      id: string
      matched_text: string
      match_type: string
      confidence: number
      char_offset: number
      context_quote: string
    }>
  }> = []
  for (const query of audit.value.queries) {
    for (const resp of query.engine_responses) {
      responses.push(resp)
    }
  }
  return responses
})

// Polling with useIntervalFn -- called at top level for proper cleanup
const { pause, resume } = useIntervalFn(async () => {
  if (!auditId.value) return
  try {
    const data = await useApiFetch<AuditDetail>(`/audit/${auditId.value}`)
    audit.value = data
    if (data.status === 'completed' || data.status === 'failed') {
      pause()
      if (data.status === 'completed') {
        loadCompetitors(auditId.value!)
      }
    }
  } catch (err: any) {
    console.error('Polling error:', err)
    pause()
  }
}, 3000, { immediate: false })

async function startAudit(url: string) {
  creating.value = true
  apiError.value = ''

  try {
    const data = await useApiFetch<{ id: string }>('/audit/', {
      method: 'POST',
      body: { url },
    })
    auditId.value = data.id
    audit.value = { id: data.id, url, domain: '', status: 'pending', error_message: null, visibility_score: null, optimization_score: null, queries: [], dispatch_summary: null, page_scores: [] }
    resume()
  } catch (err: any) {
    apiError.value = err.data?.detail || err.message || 'Failed to start audit'
  } finally {
    creating.value = false
  }
}

async function loadCompetitors(id: string) {
  try {
    const data = await useApiFetch<LeaderboardResponse>(`/competitors/${id}/leaderboard`)
    competitorLeaderboard.value = data
  } catch {
    // Competitor data is supplementary -- do not block audit experience
    competitorLeaderboard.value = null
  }
}

async function refreshAudit() {
  if (!auditId.value) return
  try {
    const data = await useApiFetch<AuditDetail>(`/audit/${auditId.value}`)
    audit.value = data
    if (data.status === 'completed') {
      loadCompetitors(auditId.value!)
    }
  } catch (err: any) {
    console.error('Refresh error:', err)
  }
}

function resetAudit() {
  auditId.value = null
  audit.value = null
  apiError.value = ''
  pause()
}
</script>
