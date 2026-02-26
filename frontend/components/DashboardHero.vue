<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    <!-- Combined GEO Score -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
      <div class="flex items-center justify-center mb-3">
        <ChartBarIcon class="w-5 h-5 text-primary-800 mr-2" />
        <span class="text-sm font-medium text-gray-500 uppercase tracking-wide">Combined GEO Score</span>
      </div>
      <div
        class="inline-flex items-center justify-center w-24 h-24 rounded-full border-4 mb-2"
        :class="getScoreBorder(combinedScore)"
      >
        <span class="text-5xl font-bold font-mono" :class="getScoreColor(combinedScore)">
          {{ combinedScore }}
        </span>
      </div>
      <DeltaBadge v-if="combinedDelta != null" :delta="combinedDelta" />
      <p class="text-xs text-gray-500">50% Visibility + 50% Optimization</p>
    </div>

    <!-- Visibility Score -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
      <div class="flex items-center justify-center mb-3">
        <EyeIcon class="w-5 h-5 text-primary-500 mr-2" />
        <span class="text-sm font-medium text-gray-500 uppercase tracking-wide">AI Visibility</span>
      </div>
      <div
        class="inline-flex items-center justify-center w-20 h-20 rounded-full border-4 mb-2"
        :class="getScoreBorder(visibilityScore)"
      >
        <span class="text-3xl font-bold font-mono" :class="getScoreColor(visibilityScore)">
          {{ visibilityScore }}
        </span>
      </div>
      <DeltaBadge v-if="visibilityDelta != null" :delta="visibilityDelta" />
      <p class="text-xs text-gray-500">
        {{ mentionCount }} mentions | {{ queryMentionRate.toFixed(0) }}% query rate
      </p>
    </div>

    <!-- Optimization Score -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
      <div class="flex items-center justify-center mb-3">
        <WrenchScrewdriverIcon class="w-5 h-5 text-warning-500 mr-2" />
        <span class="text-sm font-medium text-gray-500 uppercase tracking-wide">Site Optimization</span>
      </div>
      <div
        class="inline-flex items-center justify-center w-20 h-20 rounded-full border-4 mb-2"
        :class="getScoreBorder(optimizationScore)"
      >
        <span class="text-3xl font-bold font-mono" :class="getScoreColor(optimizationScore)">
          {{ optimizationScore }}
        </span>
      </div>
      <DeltaBadge v-if="optimizationDelta != null" :delta="optimizationDelta" />
      <p class="text-xs text-gray-500">AI-readiness across 61 criteria</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChartBarIcon, EyeIcon, WrenchScrewdriverIcon } from '@heroicons/vue/24/outline'

defineProps<{
  combinedScore: number
  visibilityScore: number
  optimizationScore: number
  mentionCount: number
  queryMentionRate: number
  combinedDelta?: number | null
  visibilityDelta?: number | null
  optimizationDelta?: number | null
}>()

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 50) return 'text-amber-600'
  return 'text-red-600'
}

function getScoreBorder(score: number): string {
  if (score >= 80) return 'border-green-500'
  if (score >= 50) return 'border-amber-500'
  return 'border-red-500'
}
</script>
