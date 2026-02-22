<template>
  <div class="bg-white rounded-lg border border-gray-200 p-8">
    <h2 class="text-lg font-semibold text-gray-900 mb-6">Audit in Progress</h2>

    <div class="space-y-0">
      <div v-for="(step, index) in STEPS" :key="step.key" class="relative flex items-start">
        <!-- Connecting line -->
        <div
          v-if="index < STEPS.length - 1"
          class="absolute left-3.5 top-7 w-0.5 h-full -ml-px"
          :class="index < activeIndex ? 'bg-green-500' : 'bg-gray-200'"
        />

        <!-- Step indicator -->
        <div class="relative flex-shrink-0 mr-4">
          <!-- Completed -->
          <CheckCircleIcon
            v-if="index < activeIndex"
            class="w-7 h-7 text-green-500"
          />
          <!-- Active -->
          <div
            v-else-if="index === activeIndex && !isFailed"
            class="w-7 h-7 rounded-full border-2 border-primary-500 bg-primary-50 flex items-center justify-center animate-pulse"
          >
            <div class="w-2.5 h-2.5 rounded-full bg-primary-500" />
          </div>
          <!-- Failed -->
          <div
            v-else-if="index === activeIndex && isFailed"
            class="w-7 h-7 rounded-full border-2 border-red-500 bg-red-50 flex items-center justify-center"
          >
            <XMarkIcon class="w-4 h-4 text-red-500" />
          </div>
          <!-- Future -->
          <div
            v-else
            class="w-7 h-7 rounded-full border-2 border-gray-300 bg-white"
          />
        </div>

        <!-- Step content -->
        <div class="pb-8 min-w-0">
          <p
            class="text-sm font-medium"
            :class="{
              'text-green-700': index < activeIndex,
              'text-primary-700': index === activeIndex && !isFailed,
              'text-red-700': index === activeIndex && isFailed,
              'text-gray-500': index > activeIndex,
            }"
          >
            {{ step.label }}
          </p>
          <p class="text-xs text-gray-500 mt-0.5">{{ step.description }}</p>
        </div>
      </div>
    </div>

    <!-- Pending state message -->
    <p v-if="status === 'pending'" class="text-sm text-gray-500 mt-2">
      Starting audit...
    </p>

    <!-- Failed state message -->
    <p v-if="isFailed" class="text-sm text-red-600 mt-2">
      An error occurred during the audit. Please try again.
    </p>
  </div>
</template>

<script setup lang="ts">
import { CheckCircleIcon, XMarkIcon } from '@heroicons/vue/24/solid'

const props = defineProps<{
  status: string
}>()

const STEPS = [
  { key: 'crawling', label: 'Crawling website', description: 'Extracting AI-readiness signals' },
  { key: 'generating_queries', label: 'Generating queries', description: 'Creating industry-relevant AI queries' },
  { key: 'dispatching', label: 'Querying AI engines', description: 'Sending queries to ChatGPT, Claude, Perplexity' },
  { key: 'analyzing', label: 'Analyzing mentions', description: 'Detecting brand mentions and scoring' },
  { key: 'completed', label: 'Audit complete', description: 'Results are ready' },
] as const

const activeIndex = computed(() => {
  const idx = STEPS.findIndex(s => s.key === props.status)
  return idx === -1 ? 0 : idx
})

const isFailed = computed(() => props.status === 'failed')
</script>
