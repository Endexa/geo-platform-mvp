<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div>
      <h1 class="text-3xl font-bold text-slate-900">Competitor Discovery</h1>
      <p class="text-slate-600 mt-1">See which brands AI engines mention alongside yours</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div
        v-for="i in 3"
        :key="i"
        class="bg-white rounded-xl border border-slate-200 p-6 h-40 animate-pulse"
      >
        <div class="h-4 bg-slate-200 rounded w-2/3 mb-4" />
        <div class="h-3 bg-slate-200 rounded w-1/3 mb-3" />
        <div class="h-8 bg-slate-200 rounded w-1/2 mb-3" />
        <div class="h-3 bg-slate-200 rounded w-full" />
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="apiError" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <ExclamationTriangleIcon class="w-16 h-16 mx-auto text-warning-400" />
      <h2 class="text-lg font-semibold text-slate-700 mt-4">Something went wrong</h2>
      <p class="text-slate-500 mt-2 mb-6">{{ apiError }}</p>
      <button @click="loadData" class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2">Try Again</button>
    </div>

    <!-- No audit state (empty) -->
    <div v-else-if="!auditId" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <UsersIcon class="w-16 h-16 mx-auto text-slate-300" />
      <h2 class="text-lg font-semibold text-slate-700 mt-4">No competitors discovered yet</h2>
      <p class="text-slate-500 mt-2 mb-6">Run an audit to discover competitors</p>
      <NuxtLink
        to="/audit"
        class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
      >
        Start an Audit
      </NuxtLink>
    </div>

    <!-- Competitor data loaded -->
    <template v-else-if="leaderboard">
      <!-- Empty leaderboard -->
      <div v-if="leaderboard.competitors.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <UsersIcon class="w-16 h-16 mx-auto text-slate-300" />
        <h2 class="text-lg font-semibold text-slate-700 mt-4">No competitors discovered yet</h2>
        <p class="text-slate-500 mt-2 mb-6">AI engines did not mention other brands for this audit's queries</p>
        <NuxtLink
          to="/audit"
          class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
        >
          Run Another Audit
        </NuxtLink>
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
          class="bg-white rounded-lg border border-slate-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-slate-700">Score Competitors</h3>
              <p class="text-xs text-slate-500 mt-1">
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
          <p v-if="crawling" class="text-xs text-slate-400 mt-3">
            Scoring competitor sites... This may take 30-60 seconds.
          </p>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ExclamationTriangleIcon, UsersIcon } from '@heroicons/vue/24/outline'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})
useHead({ title: 'Competitors — Endexa' })

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
