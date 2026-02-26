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

      <!-- Download & Export Section -->
      <div v-if="isCompleted && auditId" class="bg-white rounded-lg border border-gray-200 p-6">
        <h3 class="text-lg font-semibold text-slate-800 mb-4" style="font-family: 'Fira Code', monospace;">
          Download &amp; Export
        </h3>
        <div class="flex flex-wrap gap-3">
          <button
            @click="downloadPdf(auditId!)"
            :disabled="reportDownloading || !isProUser"
            class="inline-flex items-center px-4 py-2 bg-blue-800 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors duration-200"
          >
            PDF Report
          </button>
          <button
            @click="downloadHtml(auditId!)"
            :disabled="reportDownloading || !isProUser"
            class="inline-flex items-center px-4 py-2 bg-blue-800 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors duration-200"
          >
            HTML Report
          </button>
          <button
            @click="showCsvOptions = true"
            :disabled="reportDownloading || !isProUser"
            class="inline-flex items-center px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-200"
          >
            Export to Jira (CSV)
          </button>
        </div>

        <!-- Free tier upgrade prompt -->
        <p v-if="!isProUser" class="mt-2 text-sm text-slate-500">
          <NuxtLink to="/pricing" class="text-amber-600 hover:text-amber-500 cursor-pointer">Upgrade to Pro</NuxtLink>
          to download reports and export recommendations.
        </p>

        <!-- Download error -->
        <p v-if="reportError" class="mt-2 text-sm text-red-600">{{ reportError }}</p>

        <!-- CSV Export Options -->
        <div v-if="showCsvOptions" class="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
          <div class="space-y-3">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">Group by</label>
              <select v-model="csvGrouping" class="border border-slate-300 rounded px-3 py-1.5 text-sm cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500">
                <option value="category">Category</option>
                <option value="priority">Priority</option>
                <option value="page">Page URL</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">Epic Link (optional)</label>
              <input v-model="csvEpicLink" type="text" placeholder="e.g., PROJ-123" class="border border-slate-300 rounded px-3 py-1.5 text-sm w-48 focus-visible:ring-2 focus-visible:ring-blue-500" />
            </div>
            <div class="flex gap-2">
              <button @click="doExportCsv" class="px-3 py-1.5 bg-amber-500 text-white text-sm rounded hover:bg-amber-400 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 transition-colors duration-200">
                Download CSV
              </button>
              <button @click="showCsvOptions = false" class="px-3 py-1.5 bg-slate-200 text-slate-700 text-sm rounded hover:bg-slate-300 cursor-pointer focus-visible:ring-2 focus-visible:ring-slate-400 transition-colors duration-200">
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>

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

      <!-- Recommendation Preview (shown when audit completed and recommendations exist) -->
      <div v-if="isCompleted && recProgress && recProgress.total > 0" class="bg-white rounded-lg border border-gray-200">
        <div class="p-6 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold text-gray-900">Recommendations</h3>
            <p class="text-sm text-gray-500 mt-1">Top fixes to improve your AI visibility</p>
          </div>
          <NuxtLink
            :to="`/recommendations?auditId=${auditId}`"
            class="text-sm text-primary-600 hover:text-primary-700 font-medium cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-2 py-1"
          >
            View All
          </NuxtLink>
        </div>
        <div class="p-6 space-y-4">
          <RecommendationProgress
            :progress="recProgress"
            :by-priority="recOpenByPriority"
          />
          <div v-if="topRecommendations.length > 0" class="space-y-3">
            <div
              v-for="rec in topRecommendations"
              :key="rec.id"
              class="border border-gray-200 rounded-lg p-4"
            >
              <div class="flex items-center gap-2 mb-1">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700">
                  HIGH
                </span>
                <span class="text-sm font-semibold text-gray-900 truncate">{{ rec.criterion_name }}</span>
              </div>
              <p class="text-sm text-gray-600">{{ rec.summary }}</p>
              <div class="mt-1 flex items-center gap-3 text-xs text-gray-500">
                <span>Impact: {{ rec.impact_label }}</span>
                <span>Gap: {{ rec.gap_score }}pts</span>
              </div>
            </div>
          </div>
        </div>
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

interface RecommendationPreview {
  id: string
  criterion_name: string
  summary: string
  impact_label: string
  gap_score: number
  priority: string
  status: string
}

interface RecListResponse {
  recommendations: RecommendationPreview[]
  total: number
  by_priority: Record<string, number>
  progress: { done: number; dismissed: number; open: number; total: number }
}

const auditId = ref<string | null>(null)
const audit = ref<AuditDetail | null>(null)
const creating = ref(false)
const apiError = ref('')
const competitorLeaderboard = ref<LeaderboardResponse | null>(null)
const recProgress = ref<{ done: number; dismissed: number; open: number; total: number } | null>(null)
const topRecommendations = ref<RecommendationPreview[]>([])
const recOpenByPriority = ref<{ high: number; medium: number; low: number } | undefined>(undefined)

// Report download state
const { downloadPdf, downloadHtml, downloadCsv, isDownloading: reportDownloading, downloadError: reportError } = useReports()
const { isProUser, updateTierFromAudit } = useSubscription()
const showCsvOptions = ref(false)
const csvGrouping = ref('category')
const csvEpicLink = ref('')

function doExportCsv() {
  if (!auditId.value) return
  downloadCsv(auditId.value, {
    grouping: csvGrouping.value,
    epicLink: csvEpicLink.value || undefined,
  })
  showCsvOptions.value = false
}

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
        updateTierFromAudit(data as any)
        loadCompetitors(auditId.value!)
        loadRecommendations(auditId.value!)
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

async function loadRecommendations(id: string) {
  try {
    const data = await useApiFetch<RecListResponse>(`/recommendations/${id}`)
    recProgress.value = data.progress

    // Compute open counts per priority
    const openCounts = { high: 0, medium: 0, low: 0 }
    for (const rec of data.recommendations) {
      if (rec.status === 'open' && openCounts[rec.priority as keyof typeof openCounts] !== undefined) {
        openCounts[rec.priority as keyof typeof openCounts]++
      }
    }
    recOpenByPriority.value = openCounts

    // Top 5 high-priority open recommendations for preview
    topRecommendations.value = data.recommendations
      .filter(r => r.priority === 'high' && r.status === 'open')
      .slice(0, 5)
  } catch {
    // Recommendation data is supplementary -- do not block audit experience
    recProgress.value = null
    topRecommendations.value = []
  }
}

async function refreshAudit() {
  if (!auditId.value) return
  try {
    const data = await useApiFetch<AuditDetail>(`/audit/${auditId.value}`)
    audit.value = data
    if (data.status === 'completed') {
      updateTierFromAudit(data as any)
      loadCompetitors(auditId.value!)
      loadRecommendations(auditId.value!)
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
