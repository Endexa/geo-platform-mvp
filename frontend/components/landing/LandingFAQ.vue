<template>
  <section id="faq" class="py-20 bg-slate-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div
        ref="el"
        :class="['transition-all duration-300', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']"
      >
        <p class="text-xs uppercase tracking-[0.2em] font-semibold text-primary-600 mb-3 text-center">
          FAQ
        </p>
        <h2 class="font-mono text-3xl font-bold text-slate-900 text-center">
          Common questions
        </h2>

        <div class="divide-y divide-slate-200 max-w-2xl mx-auto mt-10">
          <div
            v-for="(faq, i) in faqs"
            :key="i"
            class="py-5"
          >
            <button
              @click="openIndex = openIndex === i ? null : i"
              class="flex items-center justify-between w-full text-left cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded"
            >
              <span class="font-medium text-slate-900">{{ faq.q }}</span>
              <ChevronDownIcon
                class="w-5 h-5 text-slate-400 transition-transform duration-200 shrink-0 ml-4"
                :class="openIndex === i ? 'rotate-180' : ''"
              />
            </button>
            <div v-show="openIndex === i" class="mt-3 text-sm text-slate-600 leading-relaxed">
              {{ faq.a }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ChevronDownIcon } from '@heroicons/vue/24/outline'
import { useScrollFadeIn } from '~/composables/useScrollFadeIn'

const { el, visible } = useScrollFadeIn()

const openIndex = ref<number | null>(null)

const faqs = [
  {
    q: 'What is GEO and how is it different from SEO?',
    a: 'Generative Engine Optimization (GEO) focuses on getting your site cited by AI systems like ChatGPT, Claude, and Perplexity — not just ranked in Google. Endexa measures both: traditional SEO signals and the specific patterns AI models use to decide who to recommend.',
  },
  {
    q: 'How long does an audit take?',
    a: 'Most audits complete in 60–120 seconds. The process crawls your page, renders JavaScript, queries multiple AI engines, and evaluates all 61 criteria. Larger pages with many external checks may take up to 3 minutes.',
  },
  {
    q: 'What AI engines do you track?',
    a: 'Endexa tracks ChatGPT (OpenAI), Claude (Anthropic), Perplexity, and Google Gemini. Engines without an API key configured are gracefully skipped — your score adjusts to reflect only the engines actually queried.',
  },
  {
    q: 'What does the Free tier include?',
    a: 'Free audits analyze the Crawlability category (12 criteria), give you an overall optimization score, and surface your top 3 recommendations. It\'s enough to see where your biggest gaps are. Full access requires a Pro subscription.',
  },
  {
    q: 'Can I cancel my Pro subscription anytime?',
    a: 'Yes. Your subscription is managed through Stripe. Click \'Manage Subscription\' in Settings to cancel, change plans, or update your payment method. You keep Pro access until the end of your billing period.',
  },
  {
    q: 'Is my data secure?',
    a: 'Endexa only crawls publicly accessible pages — the same pages any user or bot can visit. We do not store your API keys. All data is transmitted over HTTPS and stored in encrypted databases. See our Security section for full details.',
  },
  {
    q: 'Do you support multi-site management?',
    a: 'Yes. Pro accounts can add multiple domains (brands) and switch between them from the dashboard. Enterprise accounts get unlimited sites and priority support.',
  },
]
</script>
