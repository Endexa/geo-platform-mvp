// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },

  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
  ],

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiUrl: process.env.NUXT_PUBLIC_API_URL || 'http://localhost:8000',
      stripePublishableKey: process.env.NUXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '',
      stripePriceProMonthly: process.env.NUXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY || '',
    }
  },

  app: {
    head: {
      title: 'Endexa — AI Search Optimization Platform',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Endexa analyzes 61 criteria across crawlability, content structure, schema, and authority to optimize your presence in AI search engines.' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        {
          rel: 'preconnect',
          href: 'https://fonts.googleapis.com'
        },
        {
          rel: 'preconnect',
          href: 'https://fonts.gstatic.com',
          crossorigin: ''
        },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap'
        }
      ]
    }
  },

  tailwindcss: {
    cssPath: '~/assets/css/main.css',
    configPath: 'tailwind.config',
    exposeConfig: false,
    viewer: true
  },

  compatibilityDate: '2024-01-10'
})
