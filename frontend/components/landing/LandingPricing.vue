<template>
  <section id="pricing" class="py-20 bg-white">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div
        ref="el"
        class="text-center"
        :class="['transition-all duration-300', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']"
      >
        <p class="text-xs uppercase tracking-[0.2em] font-semibold text-primary-600 mb-3">
          Pricing
        </p>
        <h2 class="font-mono text-3xl font-bold text-slate-900">
          Simple, transparent pricing
        </h2>
        <p class="text-slate-600 mt-3">
          Start free. Upgrade when you need the full picture.
        </p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mt-10 text-left">
          <!-- Free tier -->
          <div class="border border-slate-200 rounded-xl p-8 flex flex-col">
            <h3 class="font-semibold text-slate-900 text-lg">Free</h3>
            <div class="mt-4 mb-6">
              <span class="font-mono text-4xl font-bold text-slate-900">$0</span>
              <span class="text-slate-500 text-sm ml-1">/mo</span>
            </div>
            <ul class="space-y-3 mb-8 flex-1">
              <li v-for="item in freePlan.included" :key="item" class="flex items-start gap-2 text-sm text-slate-700">
                <CheckIcon class="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                {{ item }}
              </li>
              <li v-for="item in freePlan.excluded" :key="item" class="flex items-start gap-2 text-sm text-slate-400">
                <XMarkIcon class="w-4 h-4 text-slate-300 shrink-0 mt-0.5" />
                {{ item }}
              </li>
            </ul>
            <NuxtLink
              to="/audit"
              class="w-full block text-center px-6 py-3 rounded-lg border border-slate-300 text-slate-700 text-sm font-semibold hover:border-primary-400 hover:text-primary-800 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            >
              Get started free
            </NuxtLink>
          </div>

          <!-- Pro tier -->
          <div class="border-2 border-primary-800 rounded-xl p-8 shadow-lg flex flex-col relative">
            <div class="absolute -top-3.5 left-1/2 -translate-x-1/2">
              <span class="bg-primary-800 text-white text-xs font-semibold px-3 py-1 rounded-full">
                Most Popular
              </span>
            </div>
            <h3 class="font-semibold text-slate-900 text-lg">Pro</h3>
            <div class="mt-4 mb-6">
              <span class="font-mono text-4xl font-bold text-slate-900">$29</span>
              <span class="text-slate-500 text-sm ml-1">/mo</span>
            </div>
            <ul class="space-y-3 mb-8 flex-1">
              <li v-for="item in proPlan.included" :key="item" class="flex items-start gap-2 text-sm text-slate-700">
                <CheckIcon class="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                {{ item }}
              </li>
            </ul>
            <button
              @click="handleSubscribe"
              :disabled="loading"
              class="w-full px-6 py-3 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
            >
              {{ loading ? 'Redirecting...' : 'Get Pro' }}
            </button>
            <p v-if="error" class="text-xs text-red-600 mt-2 text-center">{{ error }}</p>
          </div>

          <!-- Enterprise tier -->
          <div class="border border-slate-200 rounded-xl p-8 flex flex-col">
            <h3 class="font-semibold text-slate-900 text-lg">Enterprise</h3>
            <div class="mt-4 mb-6">
              <span class="font-mono text-2xl font-bold text-slate-900">Custom pricing</span>
            </div>
            <ul class="space-y-3 mb-8 flex-1">
              <li v-for="item in enterprisePlan.included" :key="item" class="flex items-start gap-2 text-sm text-slate-700">
                <CheckIcon class="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                {{ item }}
              </li>
            </ul>
            <a
              href="mailto:hello@endexa.com"
              class="w-full block text-center px-6 py-3 rounded-lg border border-slate-300 text-slate-700 text-sm font-semibold hover:border-primary-400 hover:text-primary-800 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            >
              Contact us
            </a>
          </div>
        </div>

        <p class="text-center text-sm text-slate-500 mt-8">
          All plans include a 14-day refund policy. No questions asked.
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CheckIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useScrollFadeIn } from '~/composables/useScrollFadeIn'

const { el, visible } = useScrollFadeIn()

const config = useRuntimeConfig()
const { redirectToCheckout } = useStripe()
const loading = ref(false)
const error = ref('')

const handleSubscribe = async () => {
  const priceId = config.public.stripePriceProMonthly
  if (!priceId) {
    error.value = 'Contact support@endexa.com to subscribe'
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

const freePlan = {
  included: [
    'Crawlability audit (12 criteria)',
    'Overall Optimization Score',
    'Top 3 recommendations',
  ],
  excluded: [
    'Full 61-criteria audit',
    'AI Visibility tracking',
  ],
}

const proPlan = {
  included: [
    'Full 61-criteria audit',
    'AI Visibility Score (4 engines)',
    'All recommendations',
    'Jira CSV export',
    'Code Analysis prompt generation',
    'Multiple domains',
    'AI chat assistant',
    'Priority support',
  ],
}

const enterprisePlan = {
  included: [
    'Everything in Pro',
    'Unlimited sites',
    'Custom integrations',
    'Dedicated account manager',
    'SLA guarantee',
  ],
}
</script>
