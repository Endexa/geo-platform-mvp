<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Recommendations</h1>
        <p class="text-gray-600 mt-1">Evidence-based fixes to improve your AI visibility</p>
      </div>
      <button
        v-if="recommendations.length > 0"
        @click="exportMarkdown"
        :disabled="exporting"
        class="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2"
      >
        <ArrowDownTrayIcon class="w-4 h-4" />
        <span v-if="exporting" class="flex items-center gap-2">
          <span class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
          Exporting...
        </span>
        <span v-else>Export Fix Plan</span>
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div
        v-for="i in 4"
        :key="i"
        class="bg-white rounded-xl border border-gray-200 p-5 animate-pulse"
      >
        <div class="flex items-center gap-3 mb-3">
          <div class="h-5 w-16 bg-gray-200 rounded" />
          <div class="h-4 bg-gray-200 rounded w-1/3" />
        </div>
        <div class="h-3 bg-gray-200 rounded w-full mb-2" />
        <div class="h-3 bg-gray-200 rounded w-2/3" />
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="apiError" class="bg-white rounded-xl border border-gray-200 p-12 text-center">
      <ExclamationTriangleIcon class="w-16 h-16 mx-auto text-warning-400" />
      <h2 class="text-lg font-semibold text-gray-700 mt-4">Something went wrong</h2>
      <p class="text-gray-500 mt-2 mb-6">{{ apiError }}</p>
      <button @click="loadData" class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2">Try Again</button>
    </div>

    <!-- No audit state (empty) -->
    <div v-else-if="!auditId" class="bg-white rounded-xl border border-gray-200 p-12 text-center">
      <LightBulbIcon class="w-16 h-16 mx-auto text-gray-300" />
      <h2 class="text-lg font-semibold text-gray-700 mt-4">No recommendations yet</h2>
      <p class="text-gray-500 mt-2 mb-6">Complete an audit to get recommendations</p>
      <NuxtLink
        to="/audit"
        class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
      >
        Start an Audit
      </NuxtLink>
    </div>

    <!-- Recommendations loaded -->
    <template v-else-if="auditId">
      <!-- Empty state -->
      <div v-if="recommendations.length === 0 && !loading" class="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <LightBulbIcon class="w-16 h-16 mx-auto text-gray-300" />
        <h2 class="text-lg font-semibold text-gray-700 mt-4">No recommendations yet</h2>
        <p class="text-gray-500 mt-2 mb-6">Complete an audit to get recommendations</p>
        <NuxtLink
          to="/audit"
          class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
        >
          Start an Audit
        </NuxtLink>
      </div>

      <template v-else>
        <!-- Progress bar -->
        <RecommendationProgress
          :progress="progress"
          :by-priority="openByPriority"
        />

        <!-- Tab navigation -->
        <div class="bg-white rounded-lg border border-gray-200">
          <div class="border-b border-gray-200">
            <nav class="flex -mb-px">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                class="px-4 py-3 text-sm font-medium border-b-2 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-inset"
                :class="activeTab === tab.id
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
              >
                {{ tab.label }}
              </button>
            </nav>
          </div>

          <!-- Filter row (visible on By Priority and By Page tabs) -->
          <div v-if="activeTab === 'priority' || activeTab === 'page'" class="p-4 border-b border-gray-100 flex items-center gap-4">
            <div>
              <label class="text-xs font-medium text-gray-500 mr-2">Category</label>
              <select
                v-model="filterCategory"
                class="text-sm border border-gray-300 rounded-md px-3 py-1.5 bg-white cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1"
              >
                <option value="">All</option>
                <option value="crawlability">Crawlability</option>
                <option value="content_structure">Content Structure</option>
                <option value="structured_data">Structured Data</option>
                <option value="authority">Authority</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-medium text-gray-500 mr-2">Status</label>
              <select
                v-model="filterStatus"
                class="text-sm border border-gray-300 rounded-md px-3 py-1.5 bg-white cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1"
              >
                <option value="">All</option>
                <option value="open">Open</option>
                <option value="done">Done</option>
                <option value="dismissed">Dismissed</option>
              </select>
            </div>
          </div>

          <!-- Tab content -->
          <div class="p-4">
            <!-- By Priority tab -->
            <div v-if="activeTab === 'priority'" class="space-y-6">
              <div v-for="level in priorityLevels" :key="level.key">
                <h3 class="text-sm font-semibold mb-3" :class="level.headerClass">
                  {{ level.label }} ({{ filteredByPriority(level.key).length }})
                </h3>
                <div v-if="filteredByPriority(level.key).length > 0" class="space-y-3">
                  <RecommendationCard
                    v-for="rec in filteredByPriority(level.key)"
                    :key="rec.id"
                    :recommendation="rec"
                    @update-status="handleStatusUpdate"
                  />
                </div>
                <p v-else class="text-sm text-gray-400 italic">
                  No {{ level.key }} priority recommendations
                </p>
              </div>
            </div>

            <!-- By Page tab -->
            <div v-if="activeTab === 'page'" class="space-y-6">
              <!-- Site-wide group -->
              <div v-if="siteWideRecs.length > 0">
                <button
                  @click="togglePageGroup('site-wide')"
                  class="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-1 py-0.5"
                >
                  <ChevronRightIcon
                    class="w-4 h-4 transition-transform duration-200"
                    :class="{ 'rotate-90': expandedPages['site-wide'] }"
                  />
                  Site-wide ({{ siteWideRecs.length }})
                </button>
                <div v-show="expandedPages['site-wide']" class="space-y-3 ml-6">
                  <RecommendationCard
                    v-for="rec in siteWideRecs"
                    :key="rec.id"
                    :recommendation="rec"
                    @update-status="handleStatusUpdate"
                  />
                </div>
              </div>

              <!-- Per-page groups -->
              <div v-for="group in pageGroups" :key="group.url">
                <button
                  @click="togglePageGroup(group.url)"
                  class="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-1 py-0.5"
                >
                  <ChevronRightIcon
                    class="w-4 h-4 transition-transform duration-200"
                    :class="{ 'rotate-90': expandedPages[group.url] }"
                  />
                  {{ group.url }} ({{ group.recs.length }})
                </button>
                <div v-show="expandedPages[group.url]" class="space-y-3 ml-6">
                  <RecommendationCard
                    v-for="rec in group.recs"
                    :key="rec.id"
                    :recommendation="rec"
                    @update-status="handleStatusUpdate"
                  />
                </div>
              </div>

              <p v-if="filteredRecs.length === 0" class="text-sm text-gray-400 italic">
                No recommendations match the current filters
              </p>
            </div>

            <!-- Content Gaps tab -->
            <div v-if="activeTab === 'gaps'">
              <div v-if="contentGaps.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ContentGapCard
                  v-for="gap in contentGaps"
                  :key="gap.query_id"
                  :gap="gap"
                />
              </div>
              <p v-else class="text-sm text-gray-400 italic">
                No content gaps identified -- your brand is mentioned in all query topics
              </p>
            </div>

            <!-- Sentiment tab -->
            <div v-if="activeTab === 'sentiment'" class="space-y-6">
              <div v-if="sentimentData">
                <SentimentBreakdown :engine-sentiments="sentimentData.engine_sentiments" />
              </div>
              <p v-else class="text-sm text-gray-400 italic">
                No sentiment data available. Run an audit to generate sentiment analysis.
              </p>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import {
  ArrowDownTrayIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
} from '@heroicons/vue/24/outline'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

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

interface RecommendationListResponse {
  recommendations: Recommendation[]
  total: number
  by_priority: Record<string, number>
  progress: { done: number; dismissed: number; open: number; total: number }
}

interface SentimentResponse {
  engine_sentiments: Record<string, {
    positive: number
    negative: number
    neutral: number
    total: number
    dominant: string
  }>
}

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

interface ContentGapListResponse {
  gaps: ContentGap[]
  total: number
}

interface AuditListItem {
  id: string
  url: string
  domain: string
  status: string
}

const route = useRoute()
const auditId = ref<string | null>(null)
const recommendations = ref<Recommendation[]>([])
const progress = ref({ done: 0, dismissed: 0, open: 0, total: 0 })
const byPriority = ref<Record<string, number>>({ high: 0, medium: 0, low: 0 })
const sentimentData = ref<SentimentResponse | null>(null)
const contentGaps = ref<ContentGap[]>([])
const loading = ref(true)
const apiError = ref('')
const exporting = ref(false)
const activeTab = ref('priority')
const filterCategory = ref('')
const filterStatus = ref('')
const expandedPages = ref<Record<string, boolean>>({})

const tabs = [
  { id: 'priority', label: 'By Priority' },
  { id: 'page', label: 'By Page' },
  { id: 'gaps', label: 'Content Gaps' },
  { id: 'sentiment', label: 'Sentiment' },
]

const priorityLevels = [
  { key: 'high', label: 'High Priority', headerClass: 'text-red-700' },
  { key: 'medium', label: 'Medium Priority', headerClass: 'text-amber-700' },
  { key: 'low', label: 'Low Priority', headerClass: 'text-blue-700' },
]

// Computed: open recommendation counts per priority
const openByPriority = computed(() => {
  const counts = { high: 0, medium: 0, low: 0 }
  for (const rec of recommendations.value) {
    if (rec.status === 'open' && counts[rec.priority as keyof typeof counts] !== undefined) {
      counts[rec.priority as keyof typeof counts]++
    }
  }
  return counts
})

// Filtered recommendations
const filteredRecs = computed(() => {
  let recs = recommendations.value
  if (filterCategory.value) {
    recs = recs.filter(r => r.category === filterCategory.value)
  }
  if (filterStatus.value) {
    recs = recs.filter(r => r.status === filterStatus.value)
  }
  return recs
})

function filteredByPriority(priority: string) {
  return filteredRecs.value.filter(r => r.priority === priority)
}

// Page groupings
const siteWideRecs = computed(() => {
  return filteredRecs.value.filter(r => !r.page_url)
})

const pageGroups = computed(() => {
  const groups: Record<string, Recommendation[]> = {}
  for (const rec of filteredRecs.value) {
    if (rec.page_url) {
      if (!groups[rec.page_url]) groups[rec.page_url] = []
      groups[rec.page_url].push(rec)
    }
  }
  return Object.entries(groups).map(([url, recs]) => ({ url, recs }))
})

function togglePageGroup(key: string) {
  expandedPages.value[key] = !expandedPages.value[key]
}

async function loadData() {
  loading.value = true
  apiError.value = ''

  try {
    // Determine audit_id
    let targetAuditId = route.query.auditId as string | undefined

    if (!targetAuditId) {
      // Fetch most recent completed audit
      const audits = await useApiFetch<AuditListItem[]>('/audit/', {
        params: { limit: 1 },
      })
      if (audits.length > 0 && audits[0].status === 'completed') {
        targetAuditId = audits[0].id
      }
    }

    if (!targetAuditId) {
      auditId.value = null
      loading.value = false
      return
    }

    auditId.value = targetAuditId

    // Fetch all data in parallel
    const [recData, sentData, gapData] = await Promise.all([
      useApiFetch<RecommendationListResponse>(`/recommendations/${targetAuditId}`),
      useApiFetch<SentimentResponse>(`/recommendations/${targetAuditId}/sentiment`).catch(() => null),
      useApiFetch<ContentGapListResponse>(`/recommendations/${targetAuditId}/content-gaps`).catch(() => null),
    ])

    recommendations.value = recData.recommendations
    progress.value = recData.progress
    byPriority.value = recData.by_priority
    sentimentData.value = sentData
    contentGaps.value = gapData?.gaps ?? []

    // Auto-expand all page groups
    expandedPages.value = { 'site-wide': true }
    for (const group of pageGroups.value) {
      expandedPages.value[group.url] = true
    }
  } catch (err: any) {
    apiError.value = err.data?.detail || err.message || 'Failed to load recommendations'
  } finally {
    loading.value = false
  }
}

async function handleStatusUpdate(payload: { id: string; status: 'done' | 'dismissed' | 'open' }) {
  if (!auditId.value) return

  // Optimistic update
  const recIndex = recommendations.value.findIndex(r => r.id === payload.id)
  if (recIndex === -1) return

  const prevStatus = recommendations.value[recIndex].status
  recommendations.value[recIndex] = { ...recommendations.value[recIndex], status: payload.status }
  updateProgressCounts()

  try {
    await useApiFetch(`/recommendations/${auditId.value}/${payload.id}`, {
      method: 'PATCH',
      body: { status: payload.status },
    })
  } catch (err: any) {
    // Rollback on error
    recommendations.value[recIndex] = { ...recommendations.value[recIndex], status: prevStatus }
    updateProgressCounts()
    console.error('Failed to update recommendation status:', err)
  }
}

function updateProgressCounts() {
  const counts = { done: 0, dismissed: 0, open: 0, total: recommendations.value.length }
  for (const rec of recommendations.value) {
    if (rec.status === 'done') counts.done++
    else if (rec.status === 'dismissed') counts.dismissed++
    else counts.open++
  }
  progress.value = counts
}

async function exportMarkdown() {
  if (!auditId.value || exporting.value) return

  exporting.value = true
  try {
    const blob = await useApiFetch<Blob>(`/recommendations/${auditId.value}/export/markdown`, {
      responseType: 'blob',
    })

    // Create download link
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `fix-plan-${auditId.value}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (err: any) {
    console.error('Export failed:', err)
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
