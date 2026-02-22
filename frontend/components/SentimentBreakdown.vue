<template>
  <div class="bg-white rounded-lg border border-gray-200 p-5">
    <h3 class="text-sm font-semibold text-gray-900 mb-4">Sentiment by Engine</h3>

    <div class="space-y-3">
      <div
        v-for="engine in engineList"
        :key="engine.key"
        class="flex items-center gap-3"
      >
        <!-- Engine label -->
        <span class="w-24 text-sm font-medium text-gray-700 flex-shrink-0">
          {{ engine.displayName }}
        </span>

        <!-- Sentiment bar -->
        <div v-if="engine.total > 0" class="flex-1 flex items-center gap-3">
          <div class="flex-1 flex h-3 rounded-full overflow-hidden bg-gray-100">
            <div
              v-if="engine.positive > 0"
              class="bg-green-500 transition-all duration-200"
              :style="{ width: (engine.positive / engine.total * 100) + '%' }"
            />
            <div
              v-if="engine.negative > 0"
              class="bg-red-500 transition-all duration-200"
              :style="{ width: (engine.negative / engine.total * 100) + '%' }"
            />
            <div
              v-if="engine.neutral > 0"
              class="bg-gray-400 transition-all duration-200"
              :style="{ width: (engine.neutral / engine.total * 100) + '%' }"
            />
          </div>

          <!-- Dominant label -->
          <span
            class="text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0"
            :class="dominantClasses(engine.dominant)"
          >
            {{ dominantLabel(engine.dominant) }}
          </span>

          <!-- Count -->
          <span class="text-xs text-gray-400 flex-shrink-0 w-10 text-right">
            ({{ engine.positive + engine.negative + engine.neutral }}/{{ engine.total }})
          </span>
        </div>

        <!-- Not mentioned -->
        <div v-else class="flex-1">
          <span class="text-xs text-gray-400 italic">Not mentioned</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface EngineSentiment {
  positive: number
  negative: number
  neutral: number
  total: number
  dominant: string
}

const props = defineProps<{
  engineSentiments: Record<string, EngineSentiment>
}>()

const ENGINE_DISPLAY_NAMES: Record<string, string> = {
  openai: 'ChatGPT',
  anthropic: 'Claude',
  perplexity: 'Perplexity',
  gemini: 'Gemini',
}

const ENGINE_ORDER = ['openai', 'anthropic', 'perplexity', 'gemini']

const engineList = computed(() => {
  const result: Array<EngineSentiment & { key: string; displayName: string }> = []

  for (const key of ENGINE_ORDER) {
    if (props.engineSentiments[key]) {
      result.push({
        key,
        displayName: ENGINE_DISPLAY_NAMES[key] || key,
        ...props.engineSentiments[key],
      })
    }
  }

  // Add any engines not in the predefined order
  for (const key of Object.keys(props.engineSentiments)) {
    if (!ENGINE_ORDER.includes(key)) {
      result.push({
        key,
        displayName: ENGINE_DISPLAY_NAMES[key] || key,
        ...props.engineSentiments[key],
      })
    }
  }

  return result
})

function dominantClasses(dominant: string): string {
  switch (dominant) {
    case 'positive':
      return 'bg-green-100 text-green-700'
    case 'negative':
      return 'bg-red-100 text-red-700'
    case 'neutral':
      return 'bg-gray-100 text-gray-600'
    case 'mixed':
      return 'bg-amber-100 text-amber-700'
    default:
      return 'bg-gray-100 text-gray-600'
  }
}

function dominantLabel(dominant: string): string {
  switch (dominant) {
    case 'positive':
      return 'Mostly positive'
    case 'negative':
      return 'Mostly negative'
    case 'neutral':
      return 'Neutral'
    case 'mixed':
      return 'Mixed'
    default:
      return dominant
  }
}
</script>
