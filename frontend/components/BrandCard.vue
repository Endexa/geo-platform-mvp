<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200">
    <!-- Header: Brand name + domain -->
    <div class="flex items-start justify-between mb-4">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <BuildingOfficeIcon class="w-5 h-5 text-primary-800 shrink-0" />
          <h3 class="text-lg font-semibold text-gray-900 truncate">{{ brand.brand_name }}</h3>
        </div>
        <p class="text-sm text-gray-500 mt-1 truncate">{{ brand.brand_domain }}</p>
      </div>
      <div class="flex items-center gap-1 shrink-0 ml-2">
        <button
          @click="$emit('edit', brand)"
          class="p-1.5 text-gray-400 hover:text-primary-800 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800"
          title="Edit brand"
        >
          <PencilIcon class="w-4 h-4" />
        </button>
        <button
          @click="handleDelete"
          class="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-red-500"
          title="Delete brand"
        >
          <TrashIcon class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Score trio -->
    <div v-if="hasScores" class="grid grid-cols-3 gap-3 mb-4">
      <div class="text-center">
        <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">GEO</p>
        <span
          class="text-2xl font-bold font-mono"
          :class="scoreColor(brand.combined_geo_score)"
        >
          {{ brand.combined_geo_score }}
        </span>
      </div>
      <div class="text-center">
        <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Visibility</p>
        <span
          class="text-2xl font-bold font-mono"
          :class="scoreColor(brand.visibility_score)"
        >
          {{ brand.visibility_score }}
        </span>
      </div>
      <div class="text-center">
        <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Optimization</p>
        <span
          class="text-2xl font-bold font-mono"
          :class="scoreColor(brand.optimization_score)"
        >
          {{ brand.optimization_score }}
        </span>
      </div>
    </div>
    <div v-else class="py-6 text-center text-sm text-gray-400 mb-4">
      No audit data
    </div>

    <!-- Meta info -->
    <div class="flex items-center justify-between text-xs text-gray-500 mb-4 border-t border-gray-100 pt-3">
      <span>{{ brand.audit_count }} audit{{ brand.audit_count !== 1 ? 's' : '' }}</span>
      <span v-if="brand.last_audited_at">Last audited: {{ relativeTime(brand.last_audited_at) }}</span>
      <span v-else>No audits yet</span>
    </div>

    <!-- Action button -->
    <NuxtLink
      v-if="brand.latest_audit_id"
      :to="`/dashboard`"
      class="block w-full text-center px-4 py-2 bg-primary-800 text-white rounded-lg text-sm font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
    >
      View Dashboard
    </NuxtLink>
    <NuxtLink
      v-else
      to="/audit"
      class="block w-full text-center px-4 py-2 border border-primary-800 text-primary-800 rounded-lg text-sm font-medium hover:bg-primary-800/5 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
    >
      Start Audit
    </NuxtLink>
  </div>
</template>

<script setup lang="ts">
import { BuildingOfficeIcon, PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'

interface BrandOverview {
  brand_id: string
  brand_name: string
  brand_url: string
  brand_domain: string
  latest_audit_id: string | null
  combined_geo_score: number | null
  visibility_score: number | null
  optimization_score: number | null
  mention_count: number
  top_issues_count: number
  audit_count: number
  last_audited_at: string | null
}

const props = defineProps<{
  brand: BrandOverview
}>()

const emit = defineEmits<{
  edit: [brand: BrandOverview]
  delete: [brandId: string]
}>()

const hasScores = computed(() =>
  props.brand.combined_geo_score !== null &&
  props.brand.visibility_score !== null &&
  props.brand.optimization_score !== null
)

function scoreColor(score: number | null): string {
  if (score === null) return 'text-gray-400'
  if (score >= 80) return 'text-green-600'
  if (score >= 50) return 'text-amber-600'
  return 'text-red-600'
}

function relativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays}d ago`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function handleDelete() {
  if (confirm(`Delete "${props.brand.brand_name}"? This will unlink all associated audits.`)) {
    emit('delete', props.brand.brand_id)
  }
}
</script>
