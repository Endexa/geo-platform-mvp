<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Header -->
    <div class="bg-white border-b border-slate-200">
      <div class="max-w-5xl mx-auto px-4 py-12 text-center">
        <h1 class="text-3xl font-bold text-slate-900">Choose Your Plan</h1>
        <p class="mt-3 text-lg text-slate-600">
          Start with a free crawlability audit, or unlock the full GEO analysis.
        </p>

        <!-- Billing toggle -->
        <div class="mt-8 flex items-center justify-center gap-3">
          <span
            class="text-sm font-medium"
            :class="billingPeriod === 'monthly' ? 'text-slate-900' : 'text-slate-500'"
          >
            Monthly
          </span>
          <button
            type="button"
            role="switch"
            :aria-checked="billingPeriod === 'yearly'"
            class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-blue-800 focus-visible:ring-offset-2"
            :class="billingPeriod === 'yearly' ? 'bg-blue-800' : 'bg-slate-300'"
            @click="billingPeriod = billingPeriod === 'monthly' ? 'yearly' : 'monthly'"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200"
              :class="billingPeriod === 'yearly' ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
          <span
            class="text-sm font-medium"
            :class="billingPeriod === 'yearly' ? 'text-slate-900' : 'text-slate-500'"
          >
            Yearly
            <span class="ml-1 inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              Save 17%
            </span>
          </span>
        </div>
      </div>
    </div>

    <!-- Pricing Cards -->
    <div class="max-w-5xl mx-auto px-4 py-12">
      <div class="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
        <!-- Free Tier -->
        <div class="bg-white rounded-xl border border-slate-200 p-8 flex flex-col">
          <div class="mb-6">
            <h2 class="text-xl font-semibold text-slate-900">Free</h2>
            <p class="mt-1 text-sm text-slate-500">See how AI-ready your site is</p>
          </div>
          <div class="mb-6">
            <span class="text-4xl font-bold text-slate-900">$0</span>
            <span class="text-slate-500">/month</span>
          </div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Crawlability analysis (12 criteria)</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Overall optimization score</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Top 3 recommendations</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-slate-300 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
              <span class="text-sm text-slate-400">Content structure, structured data, authority</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-slate-300 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
              <span class="text-sm text-slate-400">All recommendations + exports</span>
            </li>
          </ul>
          <button
            disabled
            class="w-full py-3 px-4 rounded-lg border border-slate-300 bg-slate-50 text-slate-500 text-sm font-medium"
          >
            Current Plan
          </button>
        </div>

        <!-- Pro Tier -->
        <div class="bg-white rounded-xl border-2 border-blue-800 p-8 flex flex-col relative">
          <div class="absolute -top-3 left-1/2 -translate-x-1/2">
            <span class="inline-flex items-center rounded-full bg-blue-800 px-3 py-1 text-xs font-semibold text-white">
              Recommended
            </span>
          </div>
          <div class="mb-6">
            <h2 class="text-xl font-semibold text-slate-900">Pro</h2>
            <p class="mt-1 text-sm text-slate-500">Full GEO analysis + actionable fixes</p>
          </div>
          <div class="mb-6">
            <span class="text-4xl font-bold text-slate-900">
              {{ billingPeriod === 'monthly' ? '$29' : '$24' }}
            </span>
            <span class="text-slate-500">/month</span>
            <span v-if="billingPeriod === 'yearly'" class="block text-sm text-slate-500 mt-1">
              Billed annually ($288/yr)
            </span>
          </div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">All 4 category analyses (61 criteria)</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">All recommendations with fix guides</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Competitor benchmarking + SOV trends</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Markdown export for AI code assistants</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">CSV/Jira export for task tracking</span>
            </li>
          </ul>
          <button
            class="w-full py-3 px-4 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
            :disabled="loading"
            @click="handleSubscribe"
          >
            <span v-if="loading">Redirecting...</span>
            <span v-else>Subscribe to Pro</span>
          </button>
          <p v-if="error" class="mt-2 text-sm text-red-600 text-center">{{ error }}</p>
        </div>
      </div>
    </div>

    <!-- FAQ or reassurance -->
    <div class="max-w-3xl mx-auto px-4 pb-16">
      <div class="bg-white rounded-xl border border-slate-200 p-6">
        <h3 class="text-sm font-semibold text-slate-900 mb-3">How it works</h3>
        <ul class="space-y-2 text-sm text-slate-600">
          <li>1. Subscribe to Pro via secure Stripe checkout</li>
          <li>2. All your audits instantly unlock full category scores and recommendations</li>
          <li>3. Manage or cancel anytime from your account settings</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
const { redirectToCheckout } = useStripe()

const billingPeriod = ref<'monthly' | 'yearly'>('monthly')
const loading = ref(false)
const error = ref('')

const handleSubscribe = async () => {
  const priceId = billingPeriod.value === 'monthly'
    ? config.public.stripePublishableKey ? 'price_pro_monthly' : ''
    : 'price_pro_yearly'

  // Use runtime config price IDs if available, otherwise show error
  if (!priceId) {
    error.value = 'Pricing not configured. Contact support.'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await redirectToCheckout(priceId)
  } catch (err: any) {
    error.value = err?.data?.detail || 'Failed to start checkout. Please try again.'
    loading.value = false
  }
}

useHead({
  title: 'Pricing - GEO Platform',
})
</script>
