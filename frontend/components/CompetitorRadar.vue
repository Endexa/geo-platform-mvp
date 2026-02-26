<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Competitive Position</h3>

    <template v-if="competitors.length > 0">
      <!-- Radar Chart -->
      <div class="h-72">
        <Radar :data="chartData" :options="chartOptions" />
      </div>

      <!-- Share of Voice Table -->
      <div class="mt-4 border-t border-gray-100 pt-4">
        <h4 class="text-sm font-medium text-gray-700 mb-2">Share of Voice</h4>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-gray-500 uppercase tracking-wider">
              <th class="pb-2">Brand</th>
              <th class="pb-2 text-right">Share of Voice</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-t border-gray-50">
              <td class="py-1.5">
                <span class="inline-block w-2.5 h-2.5 rounded-full bg-primary-800 mr-2" />
                You
              </td>
              <td class="py-1.5 text-right font-medium">{{ userSov.toFixed(1) }}%</td>
            </tr>
            <tr
              v-for="(comp, i) in competitors"
              :key="comp.name"
              class="border-t border-gray-50"
            >
              <td class="py-1.5">
                <span
                  class="inline-block w-2.5 h-2.5 rounded-full mr-2"
                  :style="{ backgroundColor: compColors[i % compColors.length] }"
                />
                {{ comp.name }}
              </td>
              <td class="py-1.5 text-right font-medium">{{ comp.share_of_voice.toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-else class="text-center py-8 text-gray-400">
      <p>No competitor data available</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Radar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'
import { chartColors, competitorColors, competitorBgColors } from '~/utils/chartColors'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

interface Scores {
  visibility: number
  optimization: number
  crawlability: number
  content: number
  schema: number
  authority: number
}

const props = defineProps<{
  userScores: Scores
  competitors: Array<{
    name: string
    share_of_voice: number
    scores: Scores
  }>
}>()

const compColors = competitorColors
const compBgColors = competitorBgColors

const userSov = computed(() => {
  const totalCompSov = props.competitors.reduce((sum, c) => sum + c.share_of_voice, 0)
  return Math.max(0, 100 - totalCompSov)
})

const chartData = computed(() => ({
  labels: ['Visibility', 'Optimization', 'Crawlability', 'Content', 'Schema', 'Authority'],
  datasets: [
    {
      label: 'Your Site',
      data: [
        props.userScores.visibility,
        props.userScores.optimization,
        props.userScores.crawlability,
        props.userScores.content,
        props.userScores.schema,
        props.userScores.authority,
      ],
      borderColor: chartColors.primary[800],
      backgroundColor: chartColors.primary.bg20,
      pointBackgroundColor: chartColors.primary[800],
      pointRadius: 3,
    },
    ...props.competitors.map((comp, i) => ({
      label: comp.name,
      data: [
        comp.scores.visibility,
        comp.scores.optimization,
        comp.scores.crawlability,
        comp.scores.content,
        comp.scores.schema,
        comp.scores.authority,
      ],
      borderColor: compColors[i % compColors.length],
      backgroundColor: compBgColors[i % compBgColors.length],
      pointBackgroundColor: compColors[i % compColors.length],
      pointRadius: 2,
    })),
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    r: {
      min: 0,
      max: 100,
      ticks: {
        stepSize: 20,
        font: { size: 10 },
      },
      pointLabels: {
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
  },
}
</script>
