import { ref, watch, type Ref } from 'vue'
import { useIntervalFn } from '@vueuse/core'

// ---------------------------------------------------------------------------
// TypeScript interfaces
// ---------------------------------------------------------------------------

interface GeneratedPrompt {
  category: string
  title: string
  prompt_text: string
  priority: string
  target_count: number
}

interface PromptsResponse {
  audit_id: string
  domain: string
  generated_at: string
  prompts: GeneratedPrompt[]
  markdown_bundle: string
}

interface CodeAnalysisResponse {
  id: string
  audit_id: string
  status: string
  detected_framework: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

interface CodeRecommendationResponse {
  id: string
  code_analysis_id: string
  criterion_id: string | null
  category: string
  severity: string
  finding: string
  file_path: string | null
  suggestion: string
  code_snippet: string | null
  evidence: string | null
  status: string
  created_at: string
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useCodeAnalysis(auditId: Ref<string>) {
  const isDownloading = ref(false)
  const isUploading = ref(false)
  const isPolling = ref(false)
  const codeAnalysis = ref<CodeAnalysisResponse | null>(null)
  const recommendations = ref<CodeRecommendationResponse[]>([])
  const error = ref<string | null>(null)

  // ---------------------------------------------------------------------------
  // Polling
  // ---------------------------------------------------------------------------

  const { pause: stopPolling, resume: startPollingFn } = useIntervalFn(
    async () => {
      await loadAnalysis()
      const status = codeAnalysis.value?.status
      if (status === 'completed' || status === 'failed') {
        stopPolling()
        isPolling.value = false
      }
    },
    3000,
    { immediate: false }
  )

  function startPolling() {
    isPolling.value = true
    startPollingFn()
  }

  // ---------------------------------------------------------------------------
  // loadRecommendations
  // ---------------------------------------------------------------------------

  async function loadRecommendations() {
    try {
      const data = await useApiFetch<CodeRecommendationResponse[]>(
        `/code-analysis/${auditId.value}/recommendations`
      )
      recommendations.value = data
    } catch {
      // Silently ignore — recommendations may not be ready yet
    }
  }

  // ---------------------------------------------------------------------------
  // loadAnalysis
  // ---------------------------------------------------------------------------

  async function loadAnalysis() {
    try {
      const data = await useApiFetch<CodeAnalysisResponse>(
        `/code-analysis/${auditId.value}`
      )
      codeAnalysis.value = data
      if (data.status === 'completed') {
        await loadRecommendations()
      } else if (data.status === 'failed') {
        error.value = data.error_message || 'Analysis failed.'
      }
    } catch (err: any) {
      // 404 means no analysis yet — that is normal, silently ignore
      const status = err?.response?.status ?? err?.status ?? err?.statusCode
      if (status !== 404) {
        error.value = err?.data?.detail || err?.message || 'Failed to load analysis.'
      }
    }
  }

  // ---------------------------------------------------------------------------
  // downloadPrompts
  // ---------------------------------------------------------------------------

  async function downloadPrompts() {
    isDownloading.value = true
    error.value = null
    try {
      const data = await useApiFetch<PromptsResponse>(
        `/code-analysis/${auditId.value}/prompts`,
        { method: 'POST' }
      )
      const blob = new Blob([data.markdown_bundle], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `endexa-analysis-prompts-${data.domain}.md`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      error.value = err?.data?.detail || err?.message || 'Failed to download prompts.'
    } finally {
      isDownloading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // uploadOutput
  // ---------------------------------------------------------------------------

  async function uploadOutput(text: string, categoriesUsed: string[]) {
    if (isUploading.value || text.trim().length < 10) return
    isUploading.value = true
    error.value = null
    try {
      const data = await useApiFetch<{ id: string; status: string }>(
        `/code-analysis/${auditId.value}/upload`,
        {
          method: 'POST',
          body: { output: text, categories_used: categoriesUsed },
        }
      )
      codeAnalysis.value = {
        id: data.id,
        audit_id: auditId.value,
        status: data.status,
        detected_framework: null,
        error_message: null,
        created_at: new Date().toISOString(),
        completed_at: null,
      }
      startPolling()
    } catch (err: any) {
      error.value = err?.data?.detail || err?.message || 'Upload failed.'
    } finally {
      isUploading.value = false
    }
  }

  // ---------------------------------------------------------------------------
  // Watch auditId — check for existing analysis when ID changes
  // ---------------------------------------------------------------------------

  watch(
    auditId,
    (newId) => {
      if (newId) {
        loadAnalysis()
      }
    },
    { immediate: true }
  )

  return {
    isDownloading,
    isUploading,
    isPolling,
    codeAnalysis,
    recommendations,
    error,
    downloadPrompts,
    uploadOutput,
    loadAnalysis,
    loadRecommendations,
  }
}
