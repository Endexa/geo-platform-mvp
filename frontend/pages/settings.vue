<template>
  <div>
    <NuxtLayout name="dashboard">
      <div class="space-y-6">
        <!-- Header -->
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Settings</h1>
          <p class="text-gray-600 mt-1">Configure your GEO Platform preferences</p>
        </div>

        <!-- Settings Sections -->
        <div class="space-y-6">
          <!-- Account Settings -->
          <div class="card">
            <h2 class="text-xl font-bold text-gray-900 mb-4">Account Settings</h2>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value="demo@endexa.com"
                  disabled
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                >
                <p class="text-xs text-gray-500 mt-1">MVP Demo Account - Authentication coming soon</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Organization</label>
                <input
                  type="text"
                  value="Endexa Demo"
                  disabled
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                >
              </div>
            </div>
          </div>

          <!-- API Settings -->
          <div class="card">
            <h2 class="text-xl font-bold text-gray-900 mb-4">API Configuration</h2>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">API Endpoint</label>
                <input
                  type="text"
                  :value="config.public.apiUrl"
                  disabled
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed font-mono text-sm"
                >
              </div>
              <div class="flex items-start space-x-2 bg-primary-50 border border-primary-200 rounded-lg p-4">
                <svg class="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div class="text-sm text-primary-800">
                  <p class="font-medium">Development Environment</p>
                  <p class="mt-1">You're currently using the local development API. Configure production settings in your .env file.</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Subscription -->
          <div class="card">
            <h2 class="text-xl font-bold text-gray-900 mb-4">Subscription</h2>
            <div class="flex items-center justify-between p-4 bg-gradient-to-r from-primary-50 to-primary-100 rounded-lg">
              <div>
                <p class="text-sm text-gray-600 mb-1">Current Plan</p>
                <p class="text-2xl font-bold text-primary-700">Free Tier</p>
                <p class="text-sm text-gray-600 mt-1">3 analyses remaining this month</p>
              </div>
              <button class="btn-primary">
                Upgrade to Pro
              </button>
            </div>
          </div>

          <!-- Security Settings -->
          <div class="card">
            <h2 class="text-xl font-bold text-gray-900 mb-4">Security</h2>
            <div class="space-y-4">
              <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p class="font-medium text-gray-900">Two-Factor Authentication</p>
                  <p class="text-sm text-gray-600">Add an extra layer of security to your account</p>
                </div>
                <span class="badge badge-warning">Coming Soon</span>
              </div>
              <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p class="font-medium text-gray-900">API Keys</p>
                  <p class="text-sm text-gray-600">Manage API keys for programmatic access</p>
                </div>
                <span class="badge badge-warning">Coming Soon</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </NuxtLayout>
  </div>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
</script>
