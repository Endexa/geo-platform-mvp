<template>
  <div class="space-y-6">
        <!-- Header -->
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Brand Voice</h1>
          <p class="text-gray-600 mt-1">Ensure consistency with hybrid AI scoring</p>
        </div>

        <!-- Coming Soon Card -->
        <div class="card text-center py-16">
          <div class="w-24 h-24 bg-primary-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg class="w-12 h-12 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
          </div>
          <h2 class="text-2xl font-bold text-gray-900 mb-3">Brand Voice Checker Coming Soon</h2>
          <p class="text-gray-600 mb-6 max-w-2xl mx-auto">
            Maintain brand consistency across all your content with our hybrid AI scoring system combining rules-based checks and semantic analysis.
          </p>
          <div class="inline-flex items-center space-x-2 bg-primary-50 text-primary-700 px-4 py-2 rounded-lg">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span class="text-sm font-medium">Feature in Development</span>
          </div>
        </div>

        <!-- Features Preview -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="card">
            <div class="flex items-start">
              <div class="w-12 h-12 bg-success-50 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg class="w-6 h-6 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
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
                <svg class="w-6 h-6 text-warning-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
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
                <svg class="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
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
definePageMeta({ layout: 'dashboard' })
// Placeholder for brand voice checker
</script>
