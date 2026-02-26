<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Brand Voice</h1>
      <p class="text-gray-600 mt-1">Ensure consistency with hybrid AI scoring</p>
    </div>

    <!-- Coming Soon Card -->
    <div class="bg-white rounded-xl border border-gray-200 p-12 text-center">
      <MicrophoneIcon class="w-16 h-16 mx-auto text-gray-300" />
      <h2 class="text-lg font-semibold text-gray-700 mt-4">Brand Voice Analysis</h2>
      <p class="text-gray-500 mt-2 mb-2">Coming in v3</p>
      <p class="text-sm text-gray-400">Statistical fingerprint and LLM deep analysis of your brand voice.</p>
    </div>

    <!-- Features Preview -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="card">
        <div class="flex items-start">
          <div class="w-12 h-12 bg-success-50 rounded-lg flex items-center justify-center flex-shrink-0">
            <CheckBadgeIcon class="w-6 h-6 text-success-600" />
          </div>
          <div class="ml-4">
            <h3 class="font-semibold text-gray-900 mb-1">Hybrid Scoring</h3>
            <p class="text-sm text-gray-600">Combines rule-based checks with semantic similarity analysis</p>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-start">
          <div class="w-12 h-12 bg-warning-50 rounded-lg flex items-center justify-center flex-shrink-0">
            <BookOpenIcon class="w-6 h-6 text-warning-600" />
          </div>
          <div class="ml-4">
            <h3 class="font-semibold text-gray-900 mb-1">Custom Rules</h3>
            <p class="text-sm text-gray-600">Define forbidden words, required phrases, and tone directives</p>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-start">
          <div class="w-12 h-12 bg-primary-50 rounded-lg flex items-center justify-center flex-shrink-0">
            <ClipboardDocumentListIcon class="w-6 h-6 text-primary-600" />
          </div>
          <div class="ml-4">
            <h3 class="font-semibold text-gray-900 mb-1">Detailed Reports</h3>
            <p class="text-sm text-gray-600">Get comprehensive feedback on brand voice consistency</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  MicrophoneIcon,
  CheckBadgeIcon,
  BookOpenIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/vue/24/outline'

definePageMeta({ layout: 'dashboard' })
</script>
