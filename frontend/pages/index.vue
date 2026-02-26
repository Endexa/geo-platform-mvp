<template>
  <div>
    <LandingHero />
    <LandingFeatures />
    <LandingHowItWorks />
    <LandingTestimonials />
    <LandingPricing />
    <LandingFAQ />
    <LandingTrust />
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'landing' })

const { isLoggedIn } = useAuth()

onMounted(() => {
  if (isLoggedIn.value) {
    navigateTo('/dashboard')
  }
})

useHead({
  title: 'Endexa — AI Search Optimization Platform',
  meta: [
    { name: 'description', content: 'Endexa analyzes 61 criteria across crawlability, content structure, schema, and authority — then tells you exactly what to fix to get cited by ChatGPT, Claude, and Perplexity.' }
  ]
})
</script>
