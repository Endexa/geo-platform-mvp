<template>
  <section id="features" class="py-20 bg-slate-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Section header with scroll fade-in -->
      <div
        ref="el"
        class="text-center"
        :class="['transition-all duration-300', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']"
      >
        <p class="text-xs uppercase tracking-[0.2em] font-semibold text-primary-600 mb-3">
          What we measure
        </p>
        <h2 class="font-mono text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
          Every signal AI uses to rank you
        </h2>
        <p class="text-slate-600 max-w-xl mx-auto">
          61 criteria across 4 categories. Real measurements from your actual page.
        </p>
      </div>

      <!-- Feature grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-12">
        <div
          v-for="card in features"
          :key="card.title"
          class="bg-white rounded-xl border border-slate-200 p-6 hover:border-primary-200 hover:shadow-md transition-all duration-200"
        >
          <div class="w-10 h-10 rounded-lg flex items-center justify-center mb-4" :class="card.iconBg">
            <component :is="card.icon" class="w-5 h-5" :class="card.iconColor" />
          </div>
          <h3 class="font-semibold text-slate-900 mb-2">{{ card.title }}</h3>
          <p class="text-sm text-slate-600 leading-relaxed">{{ card.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  ShieldCheckIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  StarIcon,
  EyeIcon,
  LightBulbIcon,
} from '@heroicons/vue/24/outline'
import { useScrollFadeIn } from '~/composables/useScrollFadeIn'

const { el, visible } = useScrollFadeIn()

const features = [
  {
    icon: ShieldCheckIcon,
    iconBg: 'bg-primary-50',
    iconColor: 'text-primary-700',
    title: 'Crawlability',
    description: '12 criteria. Bot access, SSR detection, robots.txt, sitemap, TTFB, canonical tags.',
  },
  {
    icon: DocumentTextIcon,
    iconBg: 'bg-primary-50',
    iconColor: 'text-primary-700',
    title: 'Content Structure',
    description: '13 criteria. Headings hierarchy, word count, readability, citations, list formatting.',
  },
  {
    icon: CodeBracketIcon,
    iconBg: 'bg-primary-50',
    iconColor: 'text-primary-700',
    title: 'Structured Data',
    description: '13 criteria. JSON-LD schemas, FAQPage, HowTo, llms.txt, schema type detection.',
  },
  {
    icon: StarIcon,
    iconBg: 'bg-amber-50',
    iconColor: 'text-amber-600',
    title: 'Authority',
    description: '23 criteria. E-E-A-T signals, backlinks, author bios, domain age, Wikipedia mentions.',
  },
  {
    icon: EyeIcon,
    iconBg: 'bg-primary-50',
    iconColor: 'text-primary-700',
    title: 'AI Visibility',
    description: 'Real queries sent to ChatGPT, Claude, Perplexity, and Gemini. Statistical confidence, not guesses.',
  },
  {
    icon: LightBulbIcon,
    iconBg: 'bg-amber-50',
    iconColor: 'text-amber-600',
    title: 'Actionable Fixes',
    description: 'Every gap becomes a prioritized recommendation with impact estimate and fix guide.',
  },
]
</script>
