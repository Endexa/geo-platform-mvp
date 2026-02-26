<template>
  <div>
    <!-- Section header -->
    <div class="flex items-center gap-2 mb-3">
      <h4 class="text-base font-semibold font-mono text-slate-800">Code Analysis</h4>
      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-800 uppercase tracking-wide">Pro</span>
    </div>

    <!-- Description -->
    <p class="text-sm text-gray-600 mb-4">
      Download diagnostic prompts to run on your codebase with your AI tool (Claude, ChatGPT, Copilot, etc.).
      Upload the results back to get code-specific recommendations.
    </p>

    <!-- Category pills -->
    <div class="flex flex-wrap gap-2 mb-4">
      <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
        Crawlability
      </span>
      <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
        Content Structure
      </span>
      <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
        Structured Data
      </span>
      <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
        Authority &amp; SEO
      </span>
    </div>

    <!-- Download button -->
    <button
      @click="downloadPrompts"
      :disabled="isDownloading"
      class="inline-flex items-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white text-sm font-medium rounded-lg disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 transition-colors duration-200"
    >
      <!-- Loading spinner -->
      <svg v-if="isDownloading" class="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <!-- Download icon -->
      <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
      <span>{{ isDownloading ? 'Downloading...' : 'Download Analysis Prompts' }}</span>
    </button>

    <!-- Step instructions -->
    <ol class="mt-4 space-y-1 text-sm text-gray-600 list-decimal list-inside">
      <li>Download the prompts file</li>
      <li>Open your AI tool (Claude, ChatGPT, GitHub Copilot, etc.)</li>
      <li>Share access to your codebase</li>
      <li>Paste each prompt and run it</li>
      <li>Copy the AI output and upload it below</li>
    </ol>

    <!-- Error display -->
    <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  auditId: string
}>()

const { isDownloading, error, downloadPrompts } = useCodeAnalysis(
  computed(() => props.auditId)
)
</script>
