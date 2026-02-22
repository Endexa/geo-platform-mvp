<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Competitor Discovery</h1>
      <p class="text-gray-600 mt-1">See which brands AI engines mention alongside yours</p>
    </div>

    <!-- No audit state -->
    <div v-if="!loading && !auditId" class="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <p class="text-gray-500">Run an audit first to discover competitors.</p>
      <NuxtLink
        to="/audit"
        class="inline-block mt-4 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 transition-colors duration-200"
      >
        Start an Audit
      </NuxtLink>
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <div class="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto" />
      <p class="text-gray-500 mt-4">Loading competitor data...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="apiError" class="bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-sm text-red-700">{{ apiError }}</p>
    </div>

    <!-- Competitor data loaded -->
    <template v-else-if="leaderboard">
      <!-- Empty leaderboard -->
      <div v-if="leaderboard.competitors.length === 0" class="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <p class="text-gray-500">No competitors found in AI responses.</p>
        <p class="text-sm text-gray-400 mt-1">AI engines did not mention other brands for this audit's queries.</p>
      </div>

      <template v-else>
        <!-- Leaderboard -->
        <CompetitorLeaderboard
          :competitors="leaderboard.competitors"
          :user-brand-name="leaderboard.user_brand_name"
        />

        <!-- Score Comparison -->
        <CompetitorComparison
          :user-scores="userScores"
          :competitor-audits="leaderboard.competitor_audits"
        />

        <!-- Crawl trigger -->
        <div
          v-if="uncrawledCount > 0"
          class="bg-white rounded-lg border border-gray-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-700">Score Competitors</h3>
              <p class="text-xs text-gray-500 mt-1">
                {{ uncrawledCount }} competitor{{ uncrawledCount !== 1 ? 's' : '' }} with resolved URLs ready to be scored.
              </p>
            </div>
            <button
              @click="triggerCrawl"
              :disabled="crawling"
              class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 transition-colors duration-200"
            >
              <span v-if="crawling" class="flex items-center space-x-2">
                <span class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                <span>Scoring...</span>
              </span>
              <span v-else>Score Competitors</span>
            </button>
          </div>
          <p v-if="crawling" class="text-xs text-gray-400 mt-3">
            Scoring competitor sites... This may take 30-60 seconds.
          </p>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

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

interface AuditListItem {
  id: string
  url: string
  domain: string
  status: string
}

interface AuditDetail {
  id: string
  optimization_score: {
    overall_score: number
    crawlability_avg: number
    content_structure_avg: number
    structured_data_avg: number
    authority_avg: number
    pages_scored: number
    pages_discovered: number
  } | null
}

const route = useRoute()
const auditId = ref<string | null>(null)
const leaderboard = ref<LeaderboardResponse | null>(null)
const userScores = ref<AuditDetail['optimization_score']>(null)
const loading = ref(true)
const apiError = ref('')
const crawling = ref(false)

const uncrawledCount = computed(() => {
  if (!leaderboard.value) return 0
  return leaderboard.value.competitors.filter(
    c => !c.is_user_brand && c.resolved_url && !c.is_crawled
  ).length
})

async function loadData() {
  loading.value = true
  apiError.value = ''

  try {
    // Determine audit_id
    let targetAuditId = route.query.audit_id as string | undefined

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

    // Fetch leaderboard and audit detail in parallel
    const [leaderboardData, auditDetail] = await Promise.all([
      useApiFetch<LeaderboardResponse>(`/competitors/${targetAuditId}/leaderboard`),
      useApiFetch<AuditDetail>(`/audit/${targetAuditId}`),
    ])

    leaderboard.value = leaderboardData
    userScores.value = auditDetail.optimization_score
  } catch (err: any) {
    apiError.value = err.data?.detail || err.message || 'Failed to load competitor data'
  } finally {
    loading.value = false
  }
}

async function triggerCrawl() {
  if (!auditId.value || crawling.value) return

  crawling.value = true
  apiError.value = ''

  try {
    await useApiFetch(`/competitors/${auditId.value}/crawl`, {
      method: 'POST',
    })

    // Refresh data after crawl
    await loadData()
  } catch (err: any) {
    apiError.value = err.data?.detail || err.message || 'Competitor scoring failed'
  } finally {
    crawling.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
