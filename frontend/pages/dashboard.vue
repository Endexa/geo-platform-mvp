<template>
  <div class="space-y-6">
    <!-- Header row: title + audit selector + export buttons -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p class="text-sm text-gray-500">GEO performance overview</p>
      </div>
      <div class="flex flex-col items-end gap-1">
        <div class="flex items-center gap-4">
          <select
            v-if="auditList.length > 0"
            v-model="selectedAuditId"
            class="text-sm border border-gray-300 rounded-lg px-3 py-2 focus-visible:ring-2 focus-visible:ring-[#1E40AF] cursor-pointer"
          >
            <option v-for="a in auditList" :key="a.id" :value="a.id">
              {{ a.domain }} -- {{ formatDate(a.completed_at || a.created_at) }}
            </option>
          </select>
          <ExportActions
            v-if="overview"
            :audit-id="selectedAuditId!"
            :domain="overview.domain"
          />
        </div>
        <p v-if="lastAuditedDate" class="text-xs text-gray-400">
          Last audited: {{ formatDate(lastAuditedDate) }}
        </p>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div v-for="i in 3" :key="i" class="bg-white rounded-xl border border-gray-200 p-6 h-40 animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-1/2 mb-4" />
          <div class="h-16 bg-gray-200 rounded w-1/3 mx-auto" />
        </div>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-white rounded-xl border border-gray-200 p-6 h-64 animate-pulse" />
        <div class="bg-white rounded-xl border border-gray-200 p-6 h-64 animate-pulse" />
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="bg-white rounded-xl border border-gray-200 p-12 text-center">
      <ExclamationTriangleIcon class="w-16 h-16 mx-auto text-amber-400" />
      <h2 class="text-lg font-semibold text-gray-700 mt-4">Something went wrong</h2>
      <p class="text-gray-500 mt-2 mb-6">{{ error }}</p>
      <button
        class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
        @click="retryLoad"
      >
        Try Again
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!overview"
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center"
    >
      <ShieldCheckIcon class="w-16 h-16 mx-auto text-gray-300" />
      <h2 class="text-lg font-semibold text-gray-700 mt-4">No completed audits yet</h2>
      <p class="text-gray-500 mt-2 mb-6">Run your first AI audit to see your GEO performance.</p>
      <NuxtLink
        to="/audit"
        class="inline-flex items-center px-6 py-3 bg-[#1E40AF] text-white rounded-lg font-medium hover:bg-[#1E3A8A] transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-[#1E40AF] focus-visible:ring-offset-2"
      >
        Start an Audit
      </NuxtLink>
    </div>

    <!-- Dashboard content -->
    <template v-else>
      <!-- Score hero -->
      <DashboardHero
        :combined-score="overview.combined_geo_score"
        :visibility-score="overview.visibility_score"
        :optimization-score="overview.optimization_score"
        :mention-count="overview.mention_count"
        :query-mention-rate="overview.query_mention_rate"
        :combined-delta="scoreDeltas.combined"
        :visibility-delta="scoreDeltas.visibility"
        :optimization-delta="scoreDeltas.optimization"
      />

      <!-- Two-column: Top Issues + Per-Engine Breakdown -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Top Issues -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Top Issues to Fix</h3>
          <div v-if="overview.top_issues.length > 0" class="space-y-3">
            <div
              v-for="issue in overview.top_issues"
              :key="issue.id"
              class="flex items-start gap-3 p-3 rounded-lg bg-gray-50"
            >
              <span
                class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold shrink-0 mt-0.5"
                :class="priorityClass(issue.priority)"
              >
                {{ issue.priority.toUpperCase() }}
              </span>
              <div class="min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">{{ issue.summary }}</p>
                <p class="text-xs text-gray-500">{{ issue.category.replace('_', ' ') }} | Gap: {{ issue.gap_score }}</p>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-gray-400 py-4 text-center">No open high-priority issues</p>
          <NuxtLink
            to="/recommendations"
            class="mt-4 block text-center text-sm font-medium text-[#1E40AF] hover:text-[#1E3A8A] cursor-pointer"
          >
            View all recommendations
          </NuxtLink>
        </div>

        <!-- Per-Engine Breakdown -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">AI Engine Breakdown</h3>
          <div v-if="perEngineList.length > 0" class="space-y-4">
            <div v-for="item in perEngineList" :key="item.engine" class="flex items-center gap-3">
              <span class="text-sm font-medium text-gray-700 w-24 shrink-0">{{ item.displayName }}</span>
              <div class="flex-1 bg-gray-200 rounded-full h-2.5">
                <div
                  class="h-2.5 rounded-full bg-[#1E40AF] transition-all duration-300"
                  :style="{ width: Math.min(item.score, 100) + '%' }"
                />
              </div>
              <span class="text-sm font-semibold text-gray-900 w-8 text-right">{{ item.score }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-gray-400 py-4 text-center">No engine data available</p>
        </div>
      </div>

      <!-- Category Breakdown -->
      <CategoryBreakdown
        v-if="categoryScores"
        :optimization="categoryScores"
        :selected-category="null"
      />

      <!-- Competitive Position -->
      <CompetitorRadar
        :user-scores="overview.competitive_position.user_scores"
        :competitors="overview.competitive_position.competitors"
      />

      <!-- Audit History Trend (populated by Plan 09-03) -->
      <TrendChart
        v-if="auditHistory.length > 0"
        :history="auditHistory"
      />
      <div
        v-else-if="historyLoading"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
      >
        <div class="h-64 bg-gray-100 rounded animate-pulse" />
      </div>

      <!-- Recommendation Progress -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-semibold text-gray-900">Recommendation Progress</h3>
          <span class="text-sm text-gray-500">
            {{ overview.recommendation_progress.done + overview.recommendation_progress.dismissed }}/{{ overview.recommendation_progress.total }} addressed
          </span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
          <div
            class="bg-green-500 h-2.5 rounded-full transition-all duration-300"
            :style="{ width: recProgressPercent + '%' }"
          />
        </div>
        <div class="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span>
            <span class="inline-block w-2 h-2 rounded-full bg-green-400 mr-1" />
            Done: {{ overview.recommendation_progress.done }}
          </span>
          <span>
            <span class="inline-block w-2 h-2 rounded-full bg-gray-400 mr-1" />
            Dismissed: {{ overview.recommendation_progress.dismissed }}
          </span>
          <span>
            <span class="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1" />
            Open: {{ overview.recommendation_progress.open }}
          </span>
        </div>
        <NuxtLink
          to="/recommendations"
          class="mt-4 block text-center text-sm font-medium text-[#1E40AF] hover:text-[#1E3A8A] cursor-pointer"
        >
          View all recommendations
        </NuxtLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ShieldCheckIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

definePageMeta({ layout: 'dashboard' })

interface DashboardOverview {
  audit_id: string
  domain: string
  url: string
  completed_at: string | null
  combined_geo_score: number
  visibility_score: number
  optimization_score: number
  per_engine_scores: Record<string, number>
  mention_count: number
  query_mention_rate: number
  top_issues: Array<{
    id: string
    page_url: string | null
    criterion_id: string
    criterion_name: string
    category: string
    priority: string
    impact_label: string
    summary: string
    gap_score: number
  }>
  competitive_position: {
    user_scores: Record<string, number>
    competitors: Array<{
      name: string
      share_of_voice: number
      scores: Record<string, number>
    }>
  }
  recommendation_progress: {
    done: number
    dismissed: number
    open: number
    total: number
  }
}

interface AuditListItem {
  id: string
  domain: string
  url: string
  status: string
  created_at: string
  completed_at: string | null
}

interface AuditHistoryEntry {
  date: string
  combined_score: number
  visibility_score: number
  optimization_score: number
  per_engine_scores?: Record<string, number>
  crawlability_avg?: number
  content_structure_avg?: number
  structured_data_avg?: number
  authority_avg?: number
}

const loading = ref(true)
const overview = ref<DashboardOverview | null>(null)
const auditList = ref<AuditListItem[]>([])
const selectedAuditId = ref<string | null>(null)
const error = ref<string | null>(null)
const auditHistory = ref<AuditHistoryEntry[]>([])
const historyLoading = ref(false)

// Fetch user's completed audits on mount
onMounted(async () => {
  try {
    const audits = await useApiFetch<AuditListItem[]>('/audit')
    const completed = audits.filter((a: AuditListItem) => a.status === 'completed')
    auditList.value = completed

    if (completed.length > 0) {
      selectedAuditId.value = completed[0].id
    }
  } catch (e) {
    console.error('Failed to fetch audits:', e)
    error.value = 'Failed to load audits'
  } finally {
    loading.value = false
  }
})

// Watch audit selection and fetch overview + history
watch(selectedAuditId, async (newId) => {
  if (!newId) {
    overview.value = null
    return
  }

  loading.value = true
  try {
    const data = await useApiFetch<DashboardOverview>(`/dashboard/overview/${newId}`)
    overview.value = data

    // Fetch history (supplementary -- fail silently)
    historyLoading.value = true
    try {
      const historyData = await useApiFetch<{
        domain: string
        entries: AuditHistoryEntry[]
        total: number
      }>('/dashboard/history', { params: { domain: data.domain } })
      auditHistory.value = historyData.entries || []
    } catch {
      auditHistory.value = []
    } finally {
      historyLoading.value = false
    }
  } catch (e) {
    console.error('Failed to fetch dashboard overview:', e)
    overview.value = null
  } finally {
    loading.value = false
  }
})

// Computed properties
const ENGINE_DISPLAY_NAMES: Record<string, string> = {
  openai: 'ChatGPT',
  anthropic: 'Claude',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
}

const perEngineList = computed(() => {
  if (!overview.value) return []
  return Object.entries(overview.value.per_engine_scores).map(([engine, score]) => ({
    engine,
    displayName: ENGINE_DISPLAY_NAMES[engine] || engine.charAt(0).toUpperCase() + engine.slice(1),
    score,
  }))
})

const scoreDeltas = computed(() => {
  if (auditHistory.value.length < 2) {
    return { combined: null, visibility: null, optimization: null }
  }
  const latest = auditHistory.value[auditHistory.value.length - 1]
  const prev = auditHistory.value[auditHistory.value.length - 2]
  return {
    combined: latest.combined_score - prev.combined_score,
    visibility: latest.visibility_score - prev.visibility_score,
    optimization: latest.optimization_score - prev.optimization_score,
  }
})

const recProgressPercent = computed(() => {
  if (!overview.value) return 0
  const p = overview.value.recommendation_progress
  if (p.total === 0) return 0
  return Math.round(((p.done + p.dismissed) / p.total) * 100)
})

function priorityClass(priority: string): string {
  if (priority === 'high') return 'bg-red-100 text-red-700'
  if (priority === 'medium') return 'bg-amber-100 text-amber-700'
  return 'bg-green-100 text-green-700'
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// Category scores derived from latest audit history entry
const categoryScores = computed(() => {
  if (auditHistory.value.length === 0) return null
  const latest = auditHistory.value[auditHistory.value.length - 1]
  if (
    latest.crawlability_avg == null
    && latest.content_structure_avg == null
    && latest.structured_data_avg == null
    && latest.authority_avg == null
  ) {
    return null
  }
  return {
    overall_score: overview.value?.optimization_score ?? 0,
    crawlability_avg: latest.crawlability_avg ?? 0,
    content_structure_avg: latest.content_structure_avg ?? 0,
    structured_data_avg: latest.structured_data_avg ?? 0,
    authority_avg: latest.authority_avg ?? 0,
    pages_scored: 0,
    pages_discovered: 0,
  }
})

// Last audited date from selected audit
const lastAuditedDate = computed(() => {
  if (!selectedAuditId.value || auditList.value.length === 0) return null
  const audit = auditList.value.find(a => a.id === selectedAuditId.value)
  return audit?.completed_at || audit?.created_at || null
})

async function retryLoad() {
  error.value = null
  loading.value = true
  try {
    const audits = await useApiFetch<AuditListItem[]>('/audit')
    const completed = audits.filter((a: AuditListItem) => a.status === 'completed')
    auditList.value = completed
    if (completed.length > 0) {
      selectedAuditId.value = completed[0].id
    }
  } catch (e: any) {
    error.value = e?.message || 'Failed to load audits'
  } finally {
    loading.value = false
  }
}
</script>
