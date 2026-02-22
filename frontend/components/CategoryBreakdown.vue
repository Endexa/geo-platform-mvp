<template>
  <div class="bg-white rounded-lg border border-gray-200 p-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Category Breakdown</h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <button
        v-for="cat in categories"
        :key="cat.key"
        class="text-left rounded-lg border p-4 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        :class="selectedCategory === cat.key ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'"
        @click="$emit('select', cat.key)"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-gray-700">{{ cat.label }}</span>
          <span class="text-xs text-gray-400">{{ cat.weight }}%</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex-1 bg-gray-200 rounded-full h-2.5">
            <div
              class="h-2.5 rounded-full transition-all duration-200"
              :class="getBarColor(cat.score)"
              :style="{ width: cat.score + '%' }"
            />
          </div>
          <span class="text-lg font-bold font-mono min-w-[3ch] text-right" :class="getScoreText(cat.score)">
            {{ cat.score }}
          </span>
        </div>
        <p class="text-xs mt-2" :class="getStatusColor(cat.score)">
          {{ getStatusLabel(cat.score) }}
        </p>
      </button>
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

const props = defineProps<{
  optimization: OptimizationData
  selectedCategory: string | null
}>()

defineEmits<{
  select: [category: string]
}>()

const categories = computed(() => [
  { key: 'crawlability', label: 'Crawlability', weight: 25, score: props.optimization.crawlability_avg },
  { key: 'content_structure', label: 'Content Structure', weight: 25, score: props.optimization.content_structure_avg },
  { key: 'structured_data', label: 'Structured Data', weight: 20, score: props.optimization.structured_data_avg },
  { key: 'authority', label: 'Authority', weight: 15, score: props.optimization.authority_avg },
])

function getBarColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500'
  if (score >= 60) return 'bg-green-500'
  if (score >= 30) return 'bg-yellow-500'
  return 'bg-red-500'
}

function getScoreText(score: number): string {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-green-600'
  if (score >= 30) return 'text-yellow-600'
  return 'text-red-600'
}

function getStatusLabel(score: number): string {
  if (score >= 80) return 'Excellent'
  if (score >= 60) return 'Good'
  if (score >= 30) return 'Needs Work'
  return 'Poor'
}

function getStatusColor(score: number): string {
  if (score >= 80) return 'text-emerald-600'
  if (score >= 60) return 'text-green-600'
  if (score >= 30) return 'text-yellow-600'
  return 'text-red-600'
}
</script>
