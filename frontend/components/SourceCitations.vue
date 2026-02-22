<template>
  <div class="bg-white rounded-lg border border-gray-200">
    <div class="p-6 border-b border-gray-200 flex items-center justify-between">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">Source Citations</h3>
        <p class="text-sm text-gray-500 mt-1">URLs referenced by AI engines in their responses</p>
      </div>
      <span
        v-if="totalUniqueUrls > 0"
        class="text-xs font-medium px-2.5 py-1 rounded-full bg-blue-100 text-blue-700"
      >
        {{ totalUniqueUrls }} unique URL{{ totalUniqueUrls !== 1 ? 's' : '' }}
      </span>
    </div>

    <!-- Empty state -->
    <div v-if="groupedCitations.length === 0" class="p-8 text-center">
      <p class="text-gray-500">No source citations found in engine responses.</p>
    </div>

    <template v-else>
      <!-- Citations grouped by engine -->
      <div class="divide-y divide-gray-100">
        <div
          v-for="group in groupedCitations"
          :key="group.engine"
          class="p-4"
        >
          <button
            @click="toggleEngine(group.engine)"
            class="flex items-center justify-between w-full text-left cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-1"
          >
            <div class="flex items-center space-x-2">
              <span
                class="text-xs px-1.5 py-0.5 rounded font-medium"
                :class="engineBadgeColor(group.engine)"
              >
                {{ engineDisplayName(group.engine) }}
              </span>
              <span class="text-xs text-gray-500">
                {{ group.urls.length }} citation{{ group.urls.length !== 1 ? 's' : '' }}
              </span>
            </div>
            <ChevronDownIcon
              class="w-4 h-4 text-gray-400 transition-transform duration-200"
              :class="{ 'rotate-180': expandedEngines.has(group.engine) }"
            />
          </button>

          <!-- Expanded URL list -->
          <ul
            v-if="expandedEngines.has(group.engine)"
            class="mt-3 space-y-1.5 pl-2"
          >
            <li v-for="url in group.urls" :key="url" class="flex items-start space-x-2">
              <span class="text-gray-300 mt-0.5 flex-shrink-0">&bull;</span>
              <a
                :href="url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-sm text-blue-600 hover:text-blue-800 underline break-all cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                :title="url"
              >
                {{ extractDomain(url) }}
              </a>
            </li>
          </ul>

          <!-- No citations for this engine -->
          <p v-if="group.urls.length === 0 && expandedEngines.has(group.engine)" class="mt-2 pl-2 text-sm text-gray-400">
            No source citations
          </p>
        </div>
      </div>

      <!-- Cross-engine domain summary -->
      <div v-if="domainFrequencies.length > 0" class="p-4 border-t border-gray-200">
        <h4 class="text-sm font-semibold text-gray-700 mb-3">Most Referenced Domains</h4>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="domain in domainFrequencies"
            :key="domain.domain"
            class="inline-flex items-center text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700"
          >
            {{ domain.domain }}
            <span class="ml-1 text-gray-400">({{ domain.count }})</span>
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
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
  citations?: string[]
}

const props = defineProps<{
  engineResponses: EngineResponse[]
}>()

const expandedEngines = ref<Set<string>>(new Set())

function toggleEngine(engine: string) {
  const newSet = new Set(expandedEngines.value)
  if (newSet.has(engine)) {
    newSet.delete(engine)
  } else {
    newSet.add(engine)
  }
  expandedEngines.value = newSet
}

interface CitationGroup {
  engine: string
  urls: string[]
}

const groupedCitations = computed<CitationGroup[]>(() => {
  const engineMap = new Map<string, Set<string>>()

  for (const resp of props.engineResponses) {
    if (!engineMap.has(resp.engine)) {
      engineMap.set(resp.engine, new Set())
    }
    const urlSet = engineMap.get(resp.engine)!

    // Use citations field if available
    if (resp.citations && resp.citations.length > 0) {
      for (const url of resp.citations) {
        urlSet.add(url)
      }
    } else {
      // Fallback: extract URLs from response text
      const urlRegex = /https?:\/\/[^\s)>\]"',]+/g
      const matches = resp.response_text.match(urlRegex)
      if (matches) {
        for (const url of matches) {
          urlSet.add(url)
        }
      }
    }
  }

  const groups: CitationGroup[] = []
  for (const [engine, urls] of engineMap) {
    groups.push({ engine, urls: Array.from(urls).sort() })
  }

  // Sort engines by display name
  const engineOrder = ['openai', 'anthropic', 'perplexity', 'gemini']
  groups.sort((a, b) => {
    const aIdx = engineOrder.indexOf(a.engine)
    const bIdx = engineOrder.indexOf(b.engine)
    return (aIdx === -1 ? 99 : aIdx) - (bIdx === -1 ? 99 : bIdx)
  })

  return groups
})

const totalUniqueUrls = computed(() => {
  const allUrls = new Set<string>()
  for (const group of groupedCitations.value) {
    for (const url of group.urls) {
      allUrls.add(url)
    }
  }
  return allUrls.size
})

interface DomainFrequency {
  domain: string
  count: number
}

const domainFrequencies = computed<DomainFrequency[]>(() => {
  const domainCounts = new Map<string, number>()

  for (const group of groupedCitations.value) {
    for (const url of group.urls) {
      const domain = extractDomain(url)
      domainCounts.set(domain, (domainCounts.get(domain) || 0) + 1)
    }
  }

  const frequencies: DomainFrequency[] = []
  for (const [domain, count] of domainCounts) {
    frequencies.push({ domain, count })
  }

  frequencies.sort((a, b) => b.count - a.count)
  return frequencies.slice(0, 10)
})

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url)
    return parsed.hostname
  } catch {
    return url
  }
}

function engineDisplayName(engine: string): string {
  const names: Record<string, string> = {
    openai: 'ChatGPT',
    anthropic: 'Claude',
    perplexity: 'Perplexity',
    gemini: 'Gemini',
  }
  return names[engine] || engine
}

function engineBadgeColor(engine: string): string {
  const colors: Record<string, string> = {
    openai: 'bg-green-100 text-green-700',
    anthropic: 'bg-purple-100 text-purple-700',
    perplexity: 'bg-blue-100 text-blue-700',
    gemini: 'bg-amber-100 text-amber-700',
  }
  return colors[engine] || 'bg-gray-100 text-gray-700'
}
</script>
