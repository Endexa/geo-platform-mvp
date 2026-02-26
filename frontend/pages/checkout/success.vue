<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
      <!-- Loading state -->
      <template v-if="polling">
        <div class="mb-6">
          <svg class="w-12 h-12 text-blue-800 mx-auto animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
        </div>
        <h1 class="text-xl font-semibold text-slate-900">Activating your subscription...</h1>
        <p class="mt-2 text-sm text-slate-500">This usually takes just a moment.</p>
      </template>

      <!-- Success state -->
      <template v-else-if="activated">
        <div class="mb-6">
          <svg class="w-16 h-16 text-green-600 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-slate-900">You're all set!</h1>
        <p class="mt-2 text-slate-600">
          Your Pro subscription is active. All audits now include full category scores and recommendations.
        </p>
        <NuxtLink
          to="/dashboard"
          class="mt-6 inline-flex items-center justify-center w-full py-3 px-4 rounded-lg bg-blue-800 hover:bg-blue-900 text-white text-sm font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-800 focus-visible:ring-offset-2"
        >
          Go to Dashboard
        </NuxtLink>
      </template>

      <!-- Timeout state -->
      <template v-else>
        <div class="mb-6">
          <svg class="w-16 h-16 text-amber-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <h1 class="text-xl font-semibold text-slate-900">Payment received</h1>
        <p class="mt-2 text-sm text-slate-600">
          Your payment was processed. It may take a moment for your subscription to activate.
          Please refresh in a few seconds.
        </p>
        <button
          class="mt-6 w-full py-3 px-4 rounded-lg bg-blue-800 hover:bg-blue-900 text-white text-sm font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-800 focus-visible:ring-offset-2"
          @click="retryPolling"
        >
          Check again
        </button>
        <NuxtLink
          to="/dashboard"
          class="mt-3 inline-flex items-center justify-center w-full py-3 px-4 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
        >
          Go to Dashboard
        </NuxtLink>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { setTier } = useSubscription()

const polling = ref(true)
const activated = ref(false)

const sessionId = computed(() => route.query.session_id as string || '')

const pollSessionStatus = async () => {
  if (!sessionId.value) {
    polling.value = false
    return
  }

  const maxAttempts = 5
  const intervalMs = 2000

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const data = await useApiFetch<{ status: string; subscription_id?: string }>(
        `/payments/session-status?session_id=${sessionId.value}`
      )

      if (data.status === 'complete' && data.subscription_id) {
        activated.value = true
        setTier('pro')
        polling.value = false
        return
      }
    } catch {
      // Ignore errors during polling
    }

    if (attempt < maxAttempts - 1) {
      await new Promise(resolve => setTimeout(resolve, intervalMs))
    }
  }

  // Timed out
  polling.value = false
}

const retryPolling = () => {
  polling.value = true
  activated.value = false
  pollSessionStatus()
}

onMounted(() => {
  pollSessionStatus()
})

useHead({
  title: 'Subscription Activated - GEO Platform',
})
</script>
