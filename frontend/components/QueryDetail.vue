<template>
  <Disclosure v-slot="{ open }">
    <DisclosureButton class="w-full flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer text-left focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2">
      <div class="flex items-center space-x-3">
        <!-- Mention indicator -->
        <span
          class="w-2.5 h-2.5 rounded-full flex-shrink-0"
          :class="hasMentions ? 'bg-green-500' : 'bg-gray-300'"
        />
        <div>
          <span
            class="text-xs font-medium uppercase tracking-wide rounded px-2 py-0.5"
            :class="categoryColor"
          >{{ query.category }}</span>
          <p class="text-sm font-medium text-gray-900 mt-0.5">{{ query.query_text }}</p>
        </div>
      </div>
      <ChevronDownIcon
        class="w-5 h-5 text-gray-400 transition-transform duration-200 flex-shrink-0"
        :class="{ 'rotate-180': open }"
      />
    </DisclosureButton>

    <DisclosurePanel class="mt-2 space-y-3">
      <!-- One card per engine response -->
      <div
        v-for="resp in query.engine_responses"
        :key="resp.id"
        class="bg-white rounded-lg border border-gray-200 p-4"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <span class="font-medium text-sm text-gray-900">{{ engineDisplayName(resp.engine) }}</span>
            <span class="text-xs text-gray-500">{{ resp.model_version }}</span>
          </div>
          <span
            v-if="resp.mentions.length > 0"
            class="text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded"
          >
            {{ resp.mentions.length }} mention{{ resp.mentions.length > 1 ? 's' : '' }}
          </span>
          <span v-else class="text-xs text-gray-500">No mentions</span>
        </div>

        <!-- Error state -->
        <p v-if="resp.error_message" class="text-sm text-red-600">{{ resp.error_message }}</p>

        <!-- Response text with highlighted mentions -->
        <HighlightMentions
          v-else
          :text="resp.response_text"
          :mentions="resp.mentions"
        />
      </div>
    </DisclosurePanel>
  </Disclosure>
</template>

<script setup lang="ts">
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { ChevronDownIcon } from '@heroicons/vue/24/outline'

interface EngineResponse {
  id: string
  engine: string
  model_version: string
  response_text: string
  error_message: string | null
  mentions: Array<{
    id: string
    matched_text: string
    match_type: string
    confidence: number
    char_offset: number
    context_quote: string
  }>
}

const props = defineProps<{
  query: {
    id: string
    category: string
    query_text: string
    engine_responses: EngineResponse[]
  }
}>()

const hasMentions = computed(() =>
  props.query.engine_responses.some(r => r.mentions.length > 0)
)

function engineDisplayName(engine: string): string {
  const names: Record<string, string> = {
    openai: 'ChatGPT',
    anthropic: 'Claude',
    perplexity: 'Perplexity',
  }
  return names[engine] || engine
}

const categoryColor = computed(() => {
  const colors: Record<string, string> = {
    industry: 'text-blue-700 bg-blue-100',
    brand_direct: 'text-purple-700 bg-purple-100',
    comparison: 'text-orange-700 bg-orange-100',
    problem: 'text-red-700 bg-red-100',
    recommendation: 'text-green-700 bg-green-100',
  }
  return colors[props.query.category] || 'text-gray-700 bg-gray-100'
})
</script>
