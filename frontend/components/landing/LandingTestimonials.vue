<template>
  <section id="testimonials" class="py-20 bg-white">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div
        ref="el"
        class="text-center"
        :class="['transition-all duration-300', visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6']"
      >
        <p class="text-xs uppercase tracking-[0.2em] font-semibold text-primary-600 mb-3">
          What early users say
        </p>
        <h2 class="font-mono text-3xl font-bold text-slate-900">
          Built for real SEO workflows
        </h2>

        <p class="text-xs text-slate-400 text-center mb-8 mt-4">Early Access Users</p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4 max-w-5xl mx-auto">
          <div
            v-for="testimonial in testimonials"
            :key="testimonial.initials"
            class="bg-slate-50 rounded-xl border border-slate-200 p-6 text-left"
          >
            <p class="text-slate-400 text-4xl leading-none mb-2">"</p>
            <p class="text-sm text-slate-700 leading-relaxed mb-4">{{ testimonial.quote }}</p>
            <div class="flex items-center gap-3">
              <div
                class="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold shrink-0"
                :class="testimonial.avatarClass"
              >
                {{ testimonial.initials }}
              </div>
              <div>
                <p class="font-medium text-slate-900 text-sm">{{ testimonial.name }}</p>
                <p class="text-xs text-slate-500">{{ testimonial.role }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useScrollFadeIn } from '~/composables/useScrollFadeIn'

const { el, visible } = useScrollFadeIn()

const testimonials = [
  {
    initials: 'MR',
    avatarClass: 'bg-amber-100 text-amber-800',
    name: 'MR',
    role: 'Marketing Director, SaaS Agency',
    quote: 'The combination of SEO and GEO in one tool is what we\'ve been missing. Seeing exactly which AI engines cite our clients—and why—is something no other tool gives us.',
  },
  {
    initials: 'JL',
    avatarClass: 'bg-primary-100 text-primary-800',
    name: 'JL',
    role: 'In-house SEO Lead, E-commerce',
    quote: 'Endexa caught three structured data issues on our product pages that were stopping ChatGPT from mentioning us. Fixed them in a day, saw improvement within two weeks.',
  },
  {
    initials: 'AP',
    avatarClass: 'bg-slate-200 text-slate-700',
    name: 'AP',
    role: 'Freelance SEO Consultant',
    quote: 'The Jira CSV export is a game-changer for client reporting. I can go from audit to an actionable ticket backlog in under an hour.',
  },
]
</script>
