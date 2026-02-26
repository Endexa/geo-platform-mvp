<template>
  <section id="how-it-works" class="py-20 bg-white">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Section header with scroll fade-in -->
      <div
        ref="el"
        class="text-center"
        :class="['transition-all duration-300', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']"
      >
        <p class="text-xs uppercase tracking-[0.2em] font-semibold text-primary-600 mb-3">
          How it works
        </p>
        <h2 class="font-mono text-3xl font-bold text-slate-900 mb-4">
          From URL to action plan in minutes
        </h2>

        <!-- 3-step grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12 max-w-4xl mx-auto">
          <div
            v-for="(step, index) in steps"
            :key="step.num"
            class="relative text-center"
          >
            <!-- Connecting line (between steps, desktop only) -->
            <div
              v-if="index < steps.length - 1"
              aria-hidden="true"
              class="hidden md:block absolute top-6 left-[calc(50%+24px)] right-[-50%] h-px bg-slate-200"
            />

            <!-- Step number circle -->
            <div class="w-12 h-12 rounded-full bg-primary-800 text-white font-mono text-xl font-bold flex items-center justify-center mx-auto mb-4">
              {{ step.num }}
            </div>
            <h3 class="font-semibold text-slate-900 mb-2">{{ step.title }}</h3>
            <p class="text-sm text-slate-600 leading-relaxed">{{ step.description }}</p>
          </div>
        </div>

        <!-- CTA -->
        <div class="mt-12">
          <NuxtLink
            to="/audit"
            class="inline-flex items-center px-8 py-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
          >
            Analyze your site free →
          </NuxtLink>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useScrollFadeIn } from '~/composables/useScrollFadeIn'

const { el, visible } = useScrollFadeIn()

const steps = [
  {
    num: '1',
    title: 'Enter your URL',
    description: 'Paste any URL. Endexa crawls the page, renders JavaScript, and collects 61 data points automatically.',
  },
  {
    num: '2',
    title: 'Get your score',
    description: 'See your Optimization Score and AI Visibility Score with per-category breakdowns and a confidence indicator.',
  },
  {
    num: '3',
    title: 'Fix what matters',
    description: 'Prioritized recommendations, ranked by estimated impact. Export to Jira, download as PDF, or chat with AI about your results.',
  },
]
</script>
