<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
      <div class="mb-6">
        <svg class="w-16 h-16 text-slate-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </div>
      <h1 class="text-xl font-semibold text-slate-900">Checkout cancelled</h1>
      <p class="mt-2 text-sm text-slate-600">
        No charges were made. You can try again anytime.
      </p>

      <div class="mt-8 space-y-3">
        <NuxtLink
          to="/pricing"
          class="inline-flex items-center justify-center w-full py-3 px-4 rounded-lg bg-blue-800 hover:bg-blue-900 text-white text-sm font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-800 focus-visible:ring-offset-2"
        >
          Return to pricing
        </NuxtLink>
        <NuxtLink
          to="/dashboard"
          class="inline-flex items-center justify-center w-full py-3 px-4 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
        >
          Return to dashboard
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
useHead({
  title: 'Checkout Cancelled - GEO Platform',
})
</script>
