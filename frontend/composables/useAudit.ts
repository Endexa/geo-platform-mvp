import { useIntervalFn } from '@vueuse/core'

export interface AuditDetail {
  id: string
  url: string
  domain: string
  status: string
  error_message: string | null
  created_at?: string
  completed_at?: string | null
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

export interface AuditListItem {
  id: string
  url: string
  domain: string
  status: string
  created_at: string
  completed_at: string | null
  error_message: string | null
}

export const useAudit = () => {
  const auditId = useState<string | null>('audit_id', () => null)
  const audit = useState<AuditDetail | null>('audit_detail', () => null)
  const creating = useState<boolean>('audit_creating', () => false)
  const apiError = useState<string>('audit_api_error', () => '')
  const auditHistory = useState<AuditListItem[]>('audit_history', () => [])

  const isRunning = computed(() => {
    const s = audit.value?.status
    return !!s && !['completed', 'failed'].includes(s)
  })
  const isCompleted = computed(() => audit.value?.status === 'completed')
  const isPending = computed(() => audit.value?.status === 'pending')
  const isFailed = computed(() => audit.value?.status === 'failed')

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
      audit.value = {
        id: data.id,
        url,
        domain: '',
        status: 'pending',
        error_message: null,
        visibility_score: null,
        optimization_score: null,
        queries: [],
        dispatch_summary: null,
        page_scores: [],
      }
      resume()
    } catch (err: any) {
      apiError.value = err.data?.detail || err.message || 'Failed to start audit'
    } finally {
      creating.value = false
    }
  }

  function resetAudit() {
    auditId.value = null
    audit.value = null
    apiError.value = ''
    pause()
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

  function resumePolling() {
    if (auditId.value && isRunning.value) {
      resume()
    }
  }

  function pausePolling() {
    pause()
  }

  async function loadHistory() {
    try {
      const data = await useApiFetch<AuditListItem[]>('/audit/?limit=10')
      auditHistory.value = data
    } catch {
      // History is supplementary — don't break the UI
    }
  }

  async function loadAuditById(id: string) {
    auditId.value = id
    apiError.value = ''
    try {
      const data = await useApiFetch<AuditDetail>(`/audit/${id}`)
      audit.value = data
      if (data.status !== 'completed' && data.status !== 'failed') {
        resume()
      }
    } catch (err: any) {
      apiError.value = err.data?.detail || err.message || 'Failed to load audit'
      audit.value = null
    }
  }

  return {
    auditId,
    audit,
    creating,
    apiError,
    auditHistory,
    isRunning,
    isCompleted,
    isPending,
    isFailed,
    startAudit,
    resetAudit,
    refreshAudit,
    resumePolling,
    pausePolling,
    loadHistory,
    loadAuditById,
  }
}
