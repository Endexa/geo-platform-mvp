<template>
  <div class="bg-white rounded-lg border border-gray-200">
    <div class="p-6 border-b border-gray-200">
      <h3 class="text-lg font-semibold text-gray-900">Score Comparison</h3>
      <p class="text-sm text-gray-500 mt-1">Your optimization scores vs competitors by category</p>
    </div>

    <!-- Empty state -->
    <div v-if="completedAudits.length === 0" class="p-8 text-center">
      <p class="text-gray-500">No competitors scored yet.</p>
      <p class="text-sm text-gray-400 mt-1">Score competitors to see how your site compares across categories.</p>
    </div>

    <template v-else>
      <!-- Comparison table -->
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <th class="px-4 py-3">Category</th>
              <th class="px-4 py-3 text-center">Your Score</th>
              <th
                v-for="competitor in completedAudits"
                :key="competitor.id"
                class="px-4 py-3 text-center"
              >
                {{ competitor.competitor_name }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="row in categoryRows" :key="row.key" :class="row.bold ? 'bg-gray-50' : ''">
              <td class="px-4 py-3 text-sm" :class="row.bold ? 'font-semibold text-gray-900' : 'text-gray-700'">
                {{ row.label }}
              </td>

              <!-- User score -->
              <td class="px-4 py-3 text-center">
                <span
                  class="text-sm font-semibold"
                  :class="getScoreColor(row.userScore)"
                >
                  {{ row.userScore ?? '--' }}
                </span>
              </td>

              <!-- Competitor scores -->
              <td
                v-for="competitor in completedAudits"
                :key="competitor.id"
                class="px-4 py-3 text-center"
              >
                <div class="inline-flex items-center space-x-1">
                  <span
                    class="text-sm font-semibold"
                    :class="getScoreColor(getCompetitorScore(competitor, row.key))"
                  >
                    {{ getCompetitorScore(competitor, row.key) ?? '--' }}
                  </span>
                  <!-- Direction arrow -->
                  <span
                    v-if="row.userScore != null && getCompetitorScore(competitor, row.key) != null"
                    class="text-xs"
                    :class="row.userScore > getCompetitorScore(competitor, row.key)! ? 'text-green-500' : row.userScore < getCompetitorScore(competitor, row.key)! ? 'text-red-500' : 'text-gray-300'"
                  >
                    {{ row.userScore > getCompetitorScore(competitor, row.key)! ? '&#9650;' : row.userScore < getCompetitorScore(competitor, row.key)! ? '&#9660;' : '--' }}
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Score Gaps Summary -->
      <div v-if="scoreGaps.length > 0" class="p-6 border-t border-gray-200">
        <h4 class="text-sm font-semibold text-gray-700 mb-3">Score Gaps (where you trail the top competitor)</h4>
        <ul class="space-y-2">
          <li
            v-for="gap in scoreGaps"
            :key="gap.category"
            class="flex items-center justify-between text-sm"
          >
            <span class="text-gray-700">{{ gap.category }}:</span>
            <span class="text-red-600 font-medium">
              You {{ gap.userScore }} vs {{ gap.competitorName }} {{ gap.competitorScore }}
              <span class="text-xs">({{ gap.diff }} pts)</span>
            </span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
interface UserScores {
  overall_score: number
  crawlability_avg: number
  content_structure_avg: number
  structured_data_avg: number
  authority_avg: number
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

const props = defineProps<{
  userScores: UserScores | null
  competitorAudits: CompetitorAuditSummary[]
}>()

const completedAudits = computed(() =>
  props.competitorAudits.filter(ca => ca.status === 'completed')
)

interface CategoryRow {
  key: string
  label: string
  userScore: number | null
  bold: boolean
}

const categoryRows = computed<CategoryRow[]>(() => [
  {
    key: 'crawlability_avg',
    label: 'Crawlability',
    userScore: props.userScores?.crawlability_avg ?? null,
    bold: false,
  },
  {
    key: 'content_structure_avg',
    label: 'Content Structure',
    userScore: props.userScores?.content_structure_avg ?? null,
    bold: false,
  },
  {
    key: 'structured_data_avg',
    label: 'Structured Data',
    userScore: props.userScores?.structured_data_avg ?? null,
    bold: false,
  },
  {
    key: 'authority_avg',
    label: 'Authority',
    userScore: props.userScores?.authority_avg ?? null,
    bold: false,
  },
  {
    key: 'optimization_score',
    label: 'Overall Optimization Score',
    userScore: props.userScores?.overall_score ?? null,
    bold: true,
  },
])

function getCompetitorScore(competitor: CompetitorAuditSummary, key: string): number | null {
  return (competitor as any)[key] ?? null
}

function getScoreColor(score: number | null): string {
  if (score == null) return 'text-gray-400'
  if (score >= 70) return 'text-green-600'
  if (score >= 40) return 'text-yellow-600'
  return 'text-red-600'
}

interface ScoreGap {
  category: string
  userScore: number
  competitorName: string
  competitorScore: number
  diff: number
}

const scoreGaps = computed<ScoreGap[]>(() => {
  if (!props.userScores || completedAudits.value.length === 0) return []

  const categories = [
    { key: 'crawlability_avg', label: 'Crawlability', userScore: props.userScores.crawlability_avg },
    { key: 'content_structure_avg', label: 'Content Structure', userScore: props.userScores.content_structure_avg },
    { key: 'structured_data_avg', label: 'Structured Data', userScore: props.userScores.structured_data_avg },
    { key: 'authority_avg', label: 'Authority', userScore: props.userScores.authority_avg },
  ]

  const gaps: ScoreGap[] = []

  for (const cat of categories) {
    let topCompetitor: { name: string; score: number } | null = null

    for (const ca of completedAudits.value) {
      const compScore = (ca as any)[cat.key] as number | null
      if (compScore != null && (topCompetitor == null || compScore > topCompetitor.score)) {
        topCompetitor = { name: ca.competitor_name, score: compScore }
      }
    }

    if (topCompetitor && cat.userScore < topCompetitor.score) {
      gaps.push({
        category: cat.label,
        userScore: cat.userScore,
        competitorName: topCompetitor.name,
        competitorScore: topCompetitor.score,
        diff: cat.userScore - topCompetitor.score,
      })
    }
  }

  // Sort by gap size descending (most negative first)
  gaps.sort((a, b) => a.diff - b.diff)

  return gaps
})
</script>
