<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">Score Trends</h3>

      <div v-if="history.length > 0" class="flex rounded-lg border border-gray-200 overflow-hidden">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="px-3 py-1.5 text-xs font-medium transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-inset"
          :class="activeTab === tab.key
            ? 'bg-primary-800 text-white'
            : 'bg-white text-gray-600 hover:bg-gray-50'"
          :data-testid="`trend-tab-${tab.key}`"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <template v-if="history.length > 0">
      <div class="h-64">
        <Line :key="activeTab" :data="activeChartData" :options="chartOptions" />
      </div>
    </template>

    <div v-else class="text-center py-8 text-gray-400">
      <p>No audit history available</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import 'chartjs-adapter-date-fns'

ChartJS.register(
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
)

interface HistoryEntry {
  date: string
  combined_score: number
  visibility_score: number
  optimization_score: number
  per_engine_scores?: Record<string, number>
  crawlability_avg?: number
  content_structure_avg?: number
  structured_data_avg?: number
  authority_avg?: number
}

const props = defineProps<{
  history: HistoryEntry[]
}>()

type TabKey = 'overview' | 'categories' | 'engines'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'categories', label: 'Categories' },
  { key: 'engines', label: 'AI Engines' },
]

const activeTab = ref<TabKey>('overview')

const overviewChartData = computed(() => ({
  datasets: [
    {
      label: 'Combined GEO Score',
      data: props.history.map(h => ({ x: h.date, y: h.combined_score })),
      borderColor: '#1E40AF',
      backgroundColor: 'rgba(30, 64, 175, 0.1)',
      fill: true,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: '#1E40AF',
    },
    {
      label: 'Visibility',
      data: props.history.map(h => ({ x: h.date, y: h.visibility_score })),
      borderColor: '#3B82F6',
      borderDash: [5, 5],
      fill: false,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: '#3B82F6',
    },
    {
      label: 'Optimization',
      data: props.history.map(h => ({ x: h.date, y: h.optimization_score })),
      borderColor: '#F59E0B',
      borderDash: [5, 5],
      fill: false,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: '#F59E0B',
    },
  ],
}))

const categoryChartData = computed(() => ({
  datasets: [
    {
      label: 'Crawlability',
      data: props.history.map(h => ({ x: h.date, y: h.crawlability_avg ?? 0 })),
      borderColor: '#059669',
      backgroundColor: 'rgba(5, 150, 105, 0.1)',
      fill: false,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: '#059669',
    },
    {
      label: 'Content Structure',
      data: props.history.map(h => ({ x: h.date, y: h.content_structure_avg ?? 0 })),
      borderColor: '#7C3AED',
      fill: false,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: '#7C3AED',
    },
    {
      label: 'Structured Data',
      data: props.history.map(h => ({ x: h.date, y: h.structured_data_avg ?? 0 })),
      borderColor: '#DC2626',
      fill: false,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: '#DC2626',
    },
    {
      label: 'Authority',
      data: props.history.map(h => ({ x: h.date, y: h.authority_avg ?? 0 })),
      borderColor: '#D97706',
      fill: false,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: '#D97706',
    },
  ],
}))

const engineChartData = computed(() => {
  const engines = ['chatgpt', 'claude', 'perplexity', 'gemini']
  const colors: Record<string, string> = {
    chatgpt: '#10B981',
    claude: '#8B5CF6',
    perplexity: '#3B82F6',
    gemini: '#F59E0B',
  }

  return {
    datasets: engines.map(engine => ({
      label: engine.charAt(0).toUpperCase() + engine.slice(1),
      data: props.history.map(h => ({
        x: h.date,
        y: h.per_engine_scores?.[engine] ?? 0,
      })),
      borderColor: colors[engine],
      fill: false,
      tension: 0.1,
      pointRadius: 5,
      pointHoverRadius: 7,
      pointBackgroundColor: colors[engine],
    })),
  }
})

const activeChartData = computed(() => {
  switch (activeTab.value) {
    case 'categories':
      return categoryChartData.value
    case 'engines':
      return engineChartData.value
    default:
      return overviewChartData.value
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      type: 'time' as const,
      time: {
        unit: 'day' as const,
        displayFormats: {
          day: 'MMM d',
        },
      },
      title: {
        display: true,
        text: 'Date',
        font: { size: 11 },
      },
    },
    y: {
      min: 0,
      max: 100,
      title: {
        display: true,
        text: 'Score',
        font: { size: 11 },
      },
    },
  },
  plugins: {
    legend: {
      position: 'bottom' as const,
      labels: {
        font: { size: 11 },
        padding: 16,
      },
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
    },
  },
}
</script>
