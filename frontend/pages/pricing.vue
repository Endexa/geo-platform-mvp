<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Header -->
    <div class="bg-white border-b border-slate-200">
      <div class="max-w-5xl mx-auto px-4 py-12 text-center">
        <h1 class="text-3xl font-bold text-slate-900">Choose Your Plan</h1>
        <p class="mt-3 text-lg text-slate-600">
          Start with a free crawlability audit, or unlock the full GEO analysis.
        </p>
      </div>
    </div>

    <!-- Pricing Cards -->
    <div class="max-w-5xl mx-auto px-4 py-12">
      <div class="grid md:grid-cols-3 gap-8">

        <!-- Free Tier -->
        <div class="bg-white rounded-xl border border-slate-200 p-8 flex flex-col">
          <div class="mb-6">
            <h2 class="text-xl font-semibold text-slate-900">Free</h2>
            <p class="mt-1 text-sm text-slate-500">See how AI-ready your site is</p>
          </div>
          <div class="mb-6">
            <span class="text-4xl font-bold text-slate-900">$0</span>
            <span class="text-slate-500">/mo</span>
          </div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Crawlability analysis (12 criteria)</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Overall optimization score</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
              <span class="text-sm text-slate-400">Full recommendations + exports + chat</span>
            </li>
          </ul>
          <NuxtLink
            to="/audit"
            class="w-full py-3 px-4 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium text-center transition-colors duration-200 hover:bg-slate-50 cursor-pointer"
          >
            Get started free
          </NuxtLink>
        </div>

        <!-- Pro Tier -->
        <div class="bg-white rounded-xl border-2 border-primary-800 p-8 flex flex-col relative shadow-lg">
          <div class="absolute -top-3.5 left-1/2 -translate-x-1/2">
            <span class="inline-block bg-primary-800 text-white text-xs font-semibold px-3 py-1 rounded-full whitespace-nowrap">
              Most Popular
            </span>
          </div>
          <div class="mb-6">
            <h2 class="text-xl font-semibold text-slate-900">Pro</h2>
            <p class="mt-1 text-sm text-slate-500">Full GEO analysis + actionable fixes</p>
          </div>
          <div class="mb-6">
            <span class="text-4xl font-bold text-slate-900">$29</span>
            <span class="text-slate-500">/mo</span>
          </div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Everything in Free</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">All 4 categories (61 criteria)</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Full recommendations + fix guides</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Competitor benchmarking + SOV trends</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">AI visibility breakdown (ChatGPT, Claude, Perplexity, Gemini)</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">PDF/HTML reports + Jira CSV export</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">AI chat assistant for audit Q&amp;A</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Code analysis prompts for your codebase</span>
            </li>
          </ul>
          <button
            class="w-full py-3 px-4 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
            :disabled="loading"
            @click="handleSubscribe"
          >
            <span v-if="loading">Redirecting...</span>
            <span v-else>Subscribe to Pro &mdash; $29/mo</span>
          </button>
          <p v-if="error" class="mt-2 text-sm text-red-600 text-center">{{ error }}</p>
        </div>

        <!-- Enterprise Tier -->
        <div class="bg-white rounded-xl border border-slate-200 p-8 flex flex-col">
          <div class="mb-6">
            <h2 class="text-xl font-semibold text-slate-900">Enterprise</h2>
            <p class="mt-1 text-sm text-slate-500">For agencies and large teams</p>
          </div>
          <div class="mb-6">
            <span class="text-4xl font-bold text-slate-900">Custom</span>
            <span class="text-slate-500 block text-sm mt-1">Tailored to your scale</span>
          </div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Everything in Pro</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Unlimited multi-site management</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Priority support + SLA</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">Custom integrations</span>
            </li>
            <li class="flex items-start gap-2">
              <svg class="w-5 h-5 text-green-500 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span class="text-sm text-slate-700">White-glove onboarding</span>
            </li>
          </ul>
          <a
            href="mailto:hello@endexa.com"
            class="w-full py-3 px-4 rounded-lg border border-primary-800 text-primary-800 text-sm font-medium text-center transition-colors duration-200 hover:bg-primary-50 cursor-pointer"
          >
            Contact us
          </a>
        </div>

      </div>
    </div>

    <!-- How it works -->
    <div class="max-w-5xl mx-auto px-4 pb-16">
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
definePageMeta({ layout: 'dashboard' })

const config = useRuntimeConfig()
const { redirectToCheckout } = useStripe()

const loading = ref(false)
const error = ref('')

const handleSubscribe = async () => {
  const priceId = config.public.stripePriceProMonthly
  if (!priceId) {
    error.value = 'Pricing not configured. Please contact support@endexa.com'
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

useHead({ title: 'Pricing — Endexa' })
</script>
