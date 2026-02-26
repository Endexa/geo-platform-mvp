<template>
  <div class="min-h-screen bg-white">
    <header class="sticky top-0 z-50 border-b border-slate-100 bg-white/90 backdrop-blur-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Logo -->
        <NuxtLink
          to="/"
          class="font-mono text-xl font-bold text-primary-800 hover:text-primary-900 transition-colors duration-200"
        >
          Endexa
        </NuxtLink>

        <!-- Center Nav (hidden on mobile) -->
        <nav class="hidden md:flex items-center gap-8">
          <a
            href="#features"
            class="text-sm font-medium text-slate-600 hover:text-primary-800 transition-colors duration-200"
          >
            Features
          </a>
          <a
            href="#pricing"
            class="text-sm font-medium text-slate-600 hover:text-primary-800 transition-colors duration-200"
          >
            Pricing
          </a>
          <a
            href="#faq"
            class="text-sm font-medium text-slate-600 hover:text-primary-800 transition-colors duration-200"
          >
            FAQ
          </a>
        </nav>

        <!-- Right CTAs -->
        <div class="flex items-center gap-3">
          <NuxtLink
            v-if="!isLoggedIn"
            to="/login"
            class="text-sm text-slate-600 hover:text-primary-800 transition-colors duration-200"
          >
            Sign In
          </NuxtLink>
          <NuxtLink
            to="/audit"
            class="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2"
          >
            Get Started Free
          </NuxtLink>
        </div>
      </div>
    </header>

    <slot />

    <footer class="py-8 border-t border-slate-200 text-center text-sm text-slate-500">
      © 2025 Endexa. All rights reserved.
    </footer>
  </div>
</template>

<script setup lang="ts">
const { isLoggedIn } = useAuth()
</script>
