<template>
  <footer class="bg-slate-900 text-slate-400 py-16 px-4">
    <div class="max-w-7xl mx-auto">
      <!-- Top section: 5-column grid -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
        <!-- Brand column (spans 2 on md) -->
        <div class="col-span-2">
          <p class="font-mono text-xl font-bold text-white mb-2">Endexa</p>
          <p class="text-sm leading-relaxed mb-4">AI Search Optimization for the modern web.</p>
          <a
            href="mailto:support@endexa.com"
            class="text-sm hover:text-white transition-colors duration-200"
          >
            support@endexa.com
          </a>
        </div>

        <!-- Product column -->
        <div>
          <p class="text-sm font-semibold text-white mb-4">Product</p>
          <NuxtLink to="/pricing" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Pricing</NuxtLink>
          <NuxtLink to="/dashboard" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Dashboard</NuxtLink>
          <NuxtLink to="/audit" class="block text-sm hover:text-white transition-colors duration-200 mb-2">New Audit</NuxtLink>
          <NuxtLink to="/analyze" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Analyze</NuxtLink>
        </div>

        <!-- Features column -->
        <div>
          <p class="text-sm font-semibold text-white mb-4">Features</p>
          <NuxtLink to="/competitors" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Competitors</NuxtLink>
          <NuxtLink to="/recommendations" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Recommendations</NuxtLink>
          <NuxtLink to="/audit" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Reports</NuxtLink>
          <NuxtLink to="/analyze" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Code Analysis</NuxtLink>
        </div>

        <!-- Company + Legal column -->
        <div>
          <p class="text-sm font-semibold text-white mb-4">Company</p>
          <a href="#security" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Security</a>
          <a href="#" class="block text-sm hover:text-white transition-colors duration-200 mb-2">About</a>

          <p class="text-sm font-semibold text-white mt-6 mb-4">Legal</p>
          <a href="#" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Privacy Policy</a>
          <a href="#" class="block text-sm hover:text-white transition-colors duration-200 mb-2">Terms of Service</a>
        </div>
      </div>

      <!-- Bottom bar -->
      <div class="border-t border-slate-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p class="text-sm">© 2025 Endexa. All rights reserved.</p>
        <p class="text-sm">Built with FastAPI + Nuxt 3</p>
      </div>
    </div>
  </footer>
</template>
