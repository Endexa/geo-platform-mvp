<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center p-4">
    <div class="max-w-md w-full">
      <!-- Card -->
      <div class="bg-white rounded-2xl shadow-2xl p-8">
        <!-- Logo -->
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-primary-600">GEO Platform</h1>
          <p class="text-gray-600 mt-2">Generative Engine Optimization</p>
        </div>

        <!-- MVP Notice -->
        <div class="bg-primary-50 border border-primary-200 rounded-lg p-4 mb-6">
          <p class="text-sm text-primary-800 text-center">
            <strong>MVP Demo Mode</strong><br>
            Click "Continue to Dashboard" to access the platform
          </p>
        </div>

        <!-- Continue Button -->
        <button
          @click="goToDashboard"
          class="w-full bg-primary-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-primary-700 transition-colors shadow-lg hover:shadow-xl"
        >
          Continue to Dashboard
        </button>

        <!-- Features List -->
        <div class="mt-8 space-y-3">
          <div class="flex items-start">
            <svg class="w-5 h-5 text-success-600 mt-0.5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="text-sm text-gray-600">AI-powered GEO analysis</span>
          </div>
          <div class="flex items-start">
            <svg class="w-5 h-5 text-success-600 mt-0.5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="text-sm text-gray-600">Optimization recommendations</span>
          </div>
          <div class="flex items-start">
            <svg class="w-5 h-5 text-success-600 mt-0.5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="text-sm text-gray-600">Brand voice consistency checker</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="mt-8 text-center text-xs text-gray-500">
          <p>MVP Version 1.0.0 - Development Environment</p>
          <p class="mt-1">Authentication is optional for testing</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()

const goToDashboard = () => {
  // For MVP, we bypass authentication and go directly to dashboard
  router.push('/')
}
</script>
