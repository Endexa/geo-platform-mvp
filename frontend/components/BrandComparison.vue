<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Cross-Brand Comparison</h3>

    <template v-if="brandsWithScores.length >= 2">
      <div class="h-[300px]">
        <Bar :data="chartData" :options="chartOptions" />
      </div>
    </template>

    <div v-else-if="brandsWithScores.length === 1" class="text-center py-8 text-gray-400">
      <p class="text-sm">Add more brands to see comparison</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

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
  brands: BrandOverview[]
}>()

const brandsWithScores = computed(() =>
  props.brands.filter(b => b.combined_geo_score !== null)
)

const chartData = computed(() => ({
  labels: brandsWithScores.value.map(b => b.brand_name),
  datasets: [
    {
      label: 'Combined GEO',
      data: brandsWithScores.value.map(b => b.combined_geo_score ?? 0),
      backgroundColor: '#1E40AF',
      borderRadius: 4,
    },
    {
      label: 'Visibility',
      data: brandsWithScores.value.map(b => b.visibility_score ?? 0),
      backgroundColor: '#60A5FA',
      borderRadius: 4,
    },
    {
      label: 'Optimization',
      data: brandsWithScores.value.map(b => b.optimization_score ?? 0),
      backgroundColor: '#F59E0B',
      borderRadius: 4,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: {
      min: 0,
      max: 100,
      title: {
        display: true,
        text: 'Score',
        font: { size: 11 },
      },
    },
    x: {
      ticks: {
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
        usePointStyle: true,
      },
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
    },
  },
}
</script>
