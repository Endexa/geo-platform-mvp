<template>
  <div class="space-y-6">
        <!-- Header -->
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p class="text-gray-600 mt-1">Monitor your GEO performance at a glance</p>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Average GEO Score -->
          <div class="card">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600">Avg GEO Score</p>
                <p class="text-3xl font-bold mt-2" :class="getScoreColor(stats.avgGeoScore)">
                  {{ stats.avgGeoScore }}
                </p>
              </div>
              <div class="w-16 h-16 rounded-full flex items-center justify-center"
                   :class="getScoreBg(stats.avgGeoScore)">
                <svg class="w-8 h-8" :class="getScoreColor(stats.avgGeoScore)" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Total Analyses -->
          <div class="card">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600">Total Analyses</p>
                <p class="text-3xl font-bold text-gray-900 mt-2">{{ stats.totalAnalyses }}</p>
              </div>
              <div class="w-16 h-16 bg-primary-50 rounded-full flex items-center justify-center">
                <svg class="w-8 h-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Status -->
          <div class="card">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-gray-600">Status</p>
                <p class="text-lg font-semibold text-success-600 mt-2">All Systems Go</p>
              </div>
              <div class="w-16 h-16 bg-success-50 rounded-full flex items-center justify-center">
                <svg class="w-8 h-8 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- Recent Audits -->
        <div class="card">
          <h2 class="text-xl font-bold text-gray-900 mb-4">Recent Audits</h2>
          <div v-if="loading" class="space-y-3">
            <div v-for="i in 3" :key="i" class="skeleton h-16 rounded-lg"></div>
          </div>
          <div v-else-if="recentAudits.length === 0" class="text-center py-12">
            <svg class="w-16 h-16 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-gray-500 mt-4">No analyses yet. Start by analyzing a URL!</p>
            <NuxtLink to="/analyze" class="btn-primary mt-4 inline-block">
              Analyze Now
            </NuxtLink>
          </div>
          <div v-else class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-gray-200">
                  <th class="text-left py-3 px-4 text-sm font-semibold text-gray-700">Website</th>
                  <th class="text-left py-3 px-4 text-sm font-semibold text-gray-700">GEO Score</th>
                  <th class="text-left py-3 px-4 text-sm font-semibold text-gray-700">Status</th>
                  <th class="text-left py-3 px-4 text-sm font-semibold text-gray-700">Date</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="audit in recentAudits" :key="audit.id" class="border-b border-gray-100 hover:bg-gray-50">
                  <td class="py-3 px-4">{{ audit.website }}</td>
                  <td class="py-3 px-4">
                    <span class="font-semibold" :class="getScoreColor(audit.geo_score)">
                      {{ audit.geo_score }}
                    </span>
                  </td>
                  <td class="py-3 px-4">
                    <span class="badge" :class="getStatusClass(audit.status)">
                      {{ audit.status }}
                    </span>
                  </td>
                  <td class="py-3 px-4 text-gray-600 text-sm">
                    {{ formatDate(audit.created_at) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })

const config = useRuntimeConfig()
const loading = ref(true)
const stats = ref({
  avgGeoScore: 0,
  totalAnalyses: 0
})
const recentAudits = ref([])

// Fetch dashboard stats
onMounted(async () => {
  try {
    const response = await fetch(`${config.public.apiUrl}/api/v1/dashboard/stats`)
    const data = await response.json()

    stats.value = {
      avgGeoScore: Math.round(data.avg_geo_score) || 0,
      totalAnalyses: data.total_analyses || 0
    }
    recentAudits.value = data.recent_audits || []
  } catch (error) {
    console.error('Failed to fetch dashboard stats:', error)
  } finally {
    loading.value = false
  }
})

const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-success-600'
  if (score >= 50) return 'text-warning-600'
  return 'text-danger-600'
}

const getScoreBg = (score: number) => {
  if (score >= 80) return 'bg-success-50'
  if (score >= 50) return 'bg-warning-50'
  return 'bg-danger-50'
}

const getStatusClass = (status: string) => {
  if (status === 'completed') return 'badge-success'
  if (status === 'processing') return 'badge-warning'
  return 'badge-danger'
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}
</script>
