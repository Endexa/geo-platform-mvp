<template>
  <section class="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-24 pb-16 px-4">
    <!-- Dot grid background -->
    <div
      aria-hidden="true"
      class="pointer-events-none absolute inset-0"
      style="background-image: radial-gradient(circle, #cbd5e1 1px, transparent 1px); background-size: 32px 32px; opacity: 0.4;"
    />

    <!-- Main content with scroll fade-in -->
    <div
      ref="el"
      class="relative z-10 text-center max-w-4xl mx-auto"
      :class="['transition-all duration-300', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']"
    >
      <!-- Eyebrow -->
      <p class="text-xs uppercase tracking-[0.2em] font-semibold text-primary-600 mb-6">
        AI Search Optimization Platform
      </p>

      <!-- Headline -->
      <h1 class="font-mono font-bold tracking-tight text-slate-900 text-4xl sm:text-5xl md:text-6xl lg:text-7xl mb-6">
        Is your site
        <span class="relative inline-block text-primary-800">
          visible to AI?
          <span
            aria-hidden="true"
            class="absolute -bottom-1 left-0 right-0 h-1 rounded-full bg-amber-400/60"
          />
        </span>
      </h1>

      <!-- Subheadline -->
      <p class="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto mb-10">
        Endexa analyzes 61 criteria across crawlability, content structure, schema, and authority — then tells you exactly what to fix to get cited by ChatGPT, Claude, and Perplexity.
      </p>

      <!-- CTAs -->
      <div class="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
        <NuxtLink
          to="/audit"
          class="px-8 py-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
        >
          Analyze my site free
        </NuxtLink>
        <a
          href="#features"
          class="text-sm text-slate-600 hover:text-primary-800 transition-colors duration-200"
        >
          See what we measure →
        </a>
      </div>

      <!-- Stats bar -->
      <div class="flex flex-wrap items-center justify-center gap-6 sm:gap-12 text-sm text-slate-500">
        <span>
          <span class="font-mono font-bold text-slate-900">61</span> criteria measured
        </span>
        <span class="hidden sm:inline text-slate-300">|</span>
        <span>
          <span class="font-mono font-bold text-slate-900">4</span> categories analyzed
        </span>
        <span class="hidden sm:inline text-slate-300">|</span>
        <span>
          <span class="font-mono font-bold text-slate-900">4</span> AI engines tracked
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useScrollFadeIn } from '~/composables/useScrollFadeIn'

const { el, visible } = useScrollFadeIn()
</script>
