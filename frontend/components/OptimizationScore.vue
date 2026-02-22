<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <!-- Visibility Score Card -->
    <div class="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <p class="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Visibility Score</p>
      <div
        class="inline-flex items-center justify-center w-28 h-28 rounded-full border-4 mb-3"
        :class="getScoreBorder(visibilityValue)"
      >
        <span class="text-4xl font-bold font-mono" :class="getScoreText(visibilityValue)">
          {{ visibilityValue }}
        </span>
      </div>
      <p class="text-sm text-gray-600">How often AI mentions your brand</p>
    </div>

    <!-- Optimization Score Card -->
    <div class="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <p class="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">Optimization Score</p>
      <div
        class="inline-flex items-center justify-center w-28 h-28 rounded-full border-4 mb-3"
        :class="getScoreBorder(optimizationValue)"
      >
        <span class="text-4xl font-bold font-mono" :class="getScoreText(optimizationValue)">
          {{ optimizationValue }}
        </span>
      </div>
      <p class="text-sm text-gray-600">How AI-ready your site is</p>
    </div>
  </div>

  <!-- Pages Summary Bar -->
  <div v-if="optimization" class="bg-white rounded-lg border border-gray-200 p-4 mt-4">
    <div class="flex items-center justify-between text-sm">
      <span class="text-gray-600">
        {{ optimization.pages_scored }} of {{ optimization.pages_discovered }} pages scored
      </span>
      <span v-if="optimization.pages_discovered > optimization.pages_scored" class="text-gray-400">
        {{ optimization.pages_discovered - optimization.pages_scored }} pages discovered but not scored (25-page cap)
      </span>
    </div>
    <div class="mt-2 w-full bg-gray-200 rounded-full h-2">
      <div
        class="h-2 rounded-full transition-all duration-200"
        :class="optimizationValue >= 60 ? 'bg-green-500' : optimizationValue >= 30 ? 'bg-yellow-500' : 'bg-red-500'"
        :style="{ width: pagesScoredPercent + '%' }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
interface OptimizationData {
  overall_score: number
  crawlability_avg: number
  content_structure_avg: number
  structured_data_avg: number
  authority_avg: number
  pages_scored: number
  pages_discovered: number
}

interface VisibilityData {
  overall_score: number
  per_engine_scores: Record<string, number>
  mention_count: number
  query_mention_rate: number
  algorithm_version: string
}

const props = defineProps<{
  optimization: OptimizationData | null
  visibility: VisibilityData | null
}>()

const visibilityValue = computed(() => props.visibility?.overall_score ?? 0)
const optimizationValue = computed(() => props.optimization?.overall_score ?? 0)

const pagesScoredPercent = computed(() => {
  if (!props.optimization || props.optimization.pages_discovered === 0) return 0
  return Math.round((props.optimization.pages_scored / props.optimization.pages_discovered) * 100)
})

function getScoreText(score: number): string {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-green-600'
  if (score >= 30) return 'text-yellow-600'
  return 'text-red-600'
}

function getScoreBorder(score: number): string {
  if (score >= 80) return 'border-emerald-500'
  if (score >= 60) return 'border-green-500'
  if (score >= 30) return 'border-yellow-500'
  return 'border-red-500'
}
</script>
