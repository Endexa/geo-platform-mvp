<template>
  <div class="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">AI Brand Visibility Audit</h1>
        <p class="text-gray-600 mt-1">See how AI engines perceive and mention your brand</p>
      </div>

      <!-- Phase 1: URL Input (no audit started) -->
      <AuditForm v-if="!auditId" :loading="creating" @submit="startAudit" />

      <!-- Phase 2: Progress (audit running) -->
      <AuditProgress v-else-if="isRunning" :status="audit?.status ?? 'pending'" />

      <!-- Phase 3: Results (audit complete) -->
      <AuditResults v-else-if="isCompleted && audit" :audit="audit" />

      <!-- Query Editor: visible when completed or pending -->
      <QueryEditor
        v-if="audit && auditId && (isCompleted || isPending)"
        :audit-id="auditId"
        :queries="audit.queries"
        @query-added="refreshAudit"
        @query-updated="refreshAudit"
        @query-deleted="refreshAudit"
      />

      <!-- Error State -->
      <div v-else-if="isFailed" class="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <p class="text-red-600 font-medium">Audit failed</p>
        <p class="text-gray-600 mt-2">{{ audit?.error_message || 'An unexpected error occurred.' }}</p>
        <button
          @click="resetAudit"
          class="mt-4 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 transition-colors duration-200"
        >
          Try Again
        </button>
      </div>

      <!-- API Error State -->
      <div v-if="apiError" class="bg-red-50 border border-red-200 rounded-lg p-4">
        <p class="text-sm text-red-700">{{ apiError }}</p>
      </div>
    </div>
</template>

<script setup lang="ts">
import { useIntervalFn } from '@vueuse/core'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

interface AuditDetail {
  id: string
  url: string
  domain: string
  status: string
  error_message: string | null
  visibility_score: {
    overall_score: number
    per_engine_scores: Record<string, number>
    mention_count: number
    query_mention_rate: number
    algorithm_version: string
  } | null
  optimization_score: {
    overall_score: number
    crawlability_avg: number
    content_structure_avg: number
    structured_data_avg: number
    authority_avg: number
    pages_scored: number
    pages_discovered: number
  } | null
  queries: Array<{
    id: string
    category: string
    query_text: string
    sort_order: number
    is_custom: boolean
    engine_responses: Array<{
      id: string
      engine: string
      model_version: string
      response_text: string
      error_message: string | null
      mentions: Array<{
        id: string
        matched_text: string
        match_type: string
        confidence: number
        char_offset: number
        context_quote: string
      }>
    }>
  }>
  dispatch_summary: {
    total_queries: number
    total_responses: number
    total_failures: number
    engines_used: string[]
  } | null
  page_scores: Array<{
    page_url: string
    page_title: string | null
    crawlability_score: number | null
    content_structure_score: number | null
    structured_data_score: number | null
    authority_score: number | null
    overall_page_score: number | null
    internal_link_count: number
    was_scored: boolean
    criterion_results: Array<{
      criterion_id: string
      criterion_name: string
      category: string
      score: number
      max_score: number
      is_binary: boolean
      human_summary: string
      technical_detail: string
      evidence: Record<string, unknown> | null
      checked: boolean
    }>
  }>
}

const auditId = ref<string | null>(null)
const audit = ref<AuditDetail | null>(null)
const creating = ref(false)
const apiError = ref('')

const isRunning = computed(() => {
  const s = audit.value?.status
  return s && !['completed', 'failed'].includes(s)
})

const isCompleted = computed(() => audit.value?.status === 'completed')
const isPending = computed(() => audit.value?.status === 'pending')
const isFailed = computed(() => audit.value?.status === 'failed')

// Polling with useIntervalFn -- called at top level for proper cleanup
const { pause, resume } = useIntervalFn(async () => {
  if (!auditId.value) return
  try {
    const data = await useApiFetch<AuditDetail>(`/audit/${auditId.value}`)
    audit.value = data
    if (data.status === 'completed' || data.status === 'failed') {
      pause()
    }
  } catch (err: any) {
    console.error('Polling error:', err)
    pause()
  }
}, 3000, { immediate: false })

async function startAudit(url: string) {
  creating.value = true
  apiError.value = ''

  try {
    const data = await useApiFetch<{ id: string }>('/audit/', {
      method: 'POST',
      body: { url },
    })
    auditId.value = data.id
    audit.value = { id: data.id, url, domain: '', status: 'pending', error_message: null, visibility_score: null, optimization_score: null, queries: [], dispatch_summary: null, page_scores: [] }
    resume()
  } catch (err: any) {
    apiError.value = err.data?.detail || err.message || 'Failed to start audit'
  } finally {
    creating.value = false
  }
}

async function refreshAudit() {
  if (!auditId.value) return
  try {
    const data = await useApiFetch<AuditDetail>(`/audit/${auditId.value}`)
    audit.value = data
  } catch (err: any) {
    console.error('Refresh error:', err)
  }
}

function resetAudit() {
  auditId.value = null
  audit.value = null
  apiError.value = ''
  pause()
}
</script>
