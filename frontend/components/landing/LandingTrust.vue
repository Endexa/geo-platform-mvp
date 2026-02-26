<template>
  <section id="security" class="py-20 bg-white border-t border-slate-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div
        ref="el"
        class="text-center"
        :class="['transition-all duration-300', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']"
      >
        <div class="inline-flex items-center gap-2 bg-primary-50 border border-primary-100 text-primary-700 px-4 py-1.5 rounded-full text-sm font-medium mb-6">
          <ShieldCheckIcon class="w-4 h-4" />
          Security &amp; Trust
        </div>

        <h2 class="font-mono text-3xl font-bold text-slate-900">
          Built for your data security
        </h2>
        <p class="text-slate-600 mt-3">
          Your site data and API keys are handled with enterprise-grade practices.
        </p>

        <div class="grid md:grid-cols-2 gap-4 mt-10 max-w-3xl mx-auto text-left">
          <div
            v-for="section in trustSections"
            :key="section.title"
            class="bg-slate-50 border border-slate-200 rounded-xl p-6"
          >
            <div class="flex items-center gap-3 mb-4">
              <div class="w-9 h-9 bg-primary-50 rounded-lg flex items-center justify-center shrink-0">
                <component :is="section.icon" class="w-4 h-4 text-primary-700" />
              </div>
              <h3 class="font-semibold text-slate-900">{{ section.title }}</h3>
            </div>
            <ul class="space-y-2">
              <li
                v-for="item in section.items"
                :key="item"
                class="flex items-start gap-2 text-sm text-slate-600"
              >
                <CheckCircleIcon class="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                {{ item }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  ShieldCheckIcon,
  LockClosedIcon,
  EyeSlashIcon,
  ServerIcon,
  CheckCircleIcon,
} from '@heroicons/vue/24/outline'
import { useScrollFadeIn } from '~/composables/useScrollFadeIn'

const { el, visible } = useScrollFadeIn()

const trustSections = [
  {
    icon: LockClosedIcon,
    title: 'Data Protection',
    items: [
      'All data transmitted over HTTPS/TLS',
      'Databases encrypted at rest (Supabase AES-256)',
      'No storage of AI API keys — keys used in-request only',
    ],
  },
  {
    icon: ShieldCheckIcon,
    title: 'Access Control',
    items: [
      'JWT-based authentication with secure httpOnly tokens',
      'Server-side tier gating — cannot be bypassed from the frontend',
      'Per-user data isolation — you only see your own audits',
    ],
  },
  {
    icon: EyeSlashIcon,
    title: 'Privacy',
    items: [
      'We only crawl publicly accessible pages',
      'No third-party analytics or tracking on your audit data',
      'Audit data retained for your account only',
    ],
  },
  {
    icon: ServerIcon,
    title: 'Infrastructure',
    items: [
      'Hosted on Supabase + Redis (industry-standard providers)',
      'Zero-downtime deployments via containerized workers',
      '99.9% uptime SLA target',
    ],
  },
]
</script>
