<template>
  <div class="bg-white rounded-lg border border-gray-200">
    <div class="p-6 border-b border-gray-200">
      <h3 class="text-lg font-semibold text-gray-900">Competitor Leaderboard</h3>
      <p class="text-sm text-gray-500 mt-1">Share-of-voice ranking across AI engine responses</p>
    </div>

    <!-- Empty state -->
    <div v-if="competitors.length === 0" class="p-8 text-center">
      <p class="text-gray-500">No competitors discovered yet. Run an audit to discover competitors.</p>
    </div>

    <!-- Leaderboard table -->
    <div v-else class="overflow-x-auto">
      <table class="w-full">
        <thead>
          <tr class="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th class="px-4 py-3 w-10">#</th>
            <th class="px-4 py-3">Brand</th>
            <th class="px-4 py-3">Share of Voice</th>
            <th class="px-4 py-3 text-center">Mentions</th>
            <th class="px-4 py-3">Engines</th>
            <th class="px-4 py-3 text-center">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr
            v-for="(entry, index) in competitors"
            :key="entry.entity_name"
            :class="entry.is_user_brand ? 'bg-blue-50' : ''"
          >
            <!-- Rank -->
            <td class="px-4 py-3 text-sm font-medium text-gray-700">
              {{ index + 1 }}
            </td>

            <!-- Brand name + entity type badge -->
            <td class="px-4 py-3">
              <div class="flex items-center space-x-2">
                <span
                  class="text-sm font-medium"
                  :class="entry.is_user_brand ? 'text-blue-700' : 'text-gray-900'"
                >
                  {{ entry.entity_name }}
                </span>
                <span
                  class="text-xs px-1.5 py-0.5 rounded font-medium"
                  :class="entry.entity_type === 'ORG' ? 'bg-indigo-100 text-indigo-700' : 'bg-teal-100 text-teal-700'"
                >
                  {{ entry.entity_type }}
                </span>
                <span
                  v-if="entry.is_user_brand"
                  class="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium"
                >
                  You
                </span>
              </div>
            </td>

            <!-- Share of voice with bar -->
            <td class="px-4 py-3">
              <div class="flex items-center space-x-2">
                <span class="text-sm font-semibold text-gray-900 w-12 text-right">
                  {{ entry.share_of_voice.toFixed(1) }}%
                </span>
                <div class="flex-1 max-w-[120px] h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :class="entry.is_user_brand ? 'bg-blue-500' : 'bg-gray-400'"
                    :style="{ width: sovBarWidth(entry.share_of_voice) }"
                  />
                </div>
              </div>
            </td>

            <!-- Mention count -->
            <td class="px-4 py-3 text-center text-sm text-gray-700">
              {{ entry.mention_count }}
            </td>

            <!-- Engine badges -->
            <td class="px-4 py-3">
              <div class="flex items-center space-x-1">
                <span
                  v-for="(count, engine) in entry.engines_mentioned_in"
                  :key="engine"
                  class="text-xs px-1.5 py-0.5 rounded font-medium"
                  :class="engineBadgeColor(engine as string)"
                  :title="`${engineDisplayName(engine as string)}: ${count} mention${count > 1 ? 's' : ''}`"
                >
                  {{ engineShortName(engine as string) }}
                </span>
              </div>
            </td>

            <!-- Status -->
            <td class="px-4 py-3 text-center">
              <span
                v-if="entry.is_crawled && entry.competitor_audit_id"
                class="inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700"
              >
                Scored
              </span>
              <span
                v-else-if="entry.resolved_url"
                class="inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600"
              >
                Pending
              </span>
              <span
                v-else
                class="inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-600"
              >
                No URL
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
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

const props = defineProps<{
  competitors: CompetitorLeaderboardEntry[]
  userBrandName: string
}>()

const maxSov = computed(() => {
  if (props.competitors.length === 0) return 1
  return Math.max(...props.competitors.map(c => c.share_of_voice), 1)
})

function sovBarWidth(sov: number): string {
  return `${Math.round((sov / maxSov.value) * 100)}%`
}

function engineDisplayName(engine: string): string {
  const names: Record<string, string> = {
    openai: 'ChatGPT',
    anthropic: 'Claude',
    perplexity: 'Perplexity',
    gemini: 'Gemini',
  }
  return names[engine] || engine
}

function engineShortName(engine: string): string {
  const names: Record<string, string> = {
    openai: 'GPT',
    anthropic: 'Claude',
    perplexity: 'Pplx',
    gemini: 'Gemini',
  }
  return names[engine] || engine
}

function engineBadgeColor(engine: string): string {
  const colors: Record<string, string> = {
    openai: 'bg-green-100 text-green-700',
    anthropic: 'bg-purple-100 text-purple-700',
    perplexity: 'bg-blue-100 text-blue-700',
    gemini: 'bg-amber-100 text-amber-700',
  }
  return colors[engine] || 'bg-gray-100 text-gray-700'
}
</script>
