<template>
  <div>
    <!-- Error banner -->
    <div v-if="error" class="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
      <p class="text-sm text-red-700">{{ error }}</p>
    </div>

    <!-- Upload section (shown when no analysis or failed) -->
    <div v-if="!codeAnalysis || codeAnalysis.status === 'failed'">
      <h5 class="text-base font-semibold font-mono text-slate-800 mb-3">Upload Analysis Results</h5>

      <!-- Category checkboxes -->
      <div class="mb-4">
        <p class="text-sm font-medium text-gray-700 mb-2">Which prompts did you run?</p>
        <div class="flex flex-wrap gap-x-5 gap-y-2">
          <label
            v-for="cat in CATEGORIES"
            :key="cat.value"
            class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none"
          >
            <input
              type="checkbox"
              :value="cat.value"
              v-model="selectedCategories"
              class="rounded border-gray-300 text-blue-700 focus:ring-blue-500 cursor-pointer"
            />
            {{ cat.label }}
          </label>
        </div>
      </div>

      <!-- Tabs: Paste / File -->
      <div class="mb-3">
        <div class="flex border-b border-gray-200 mb-3">
          <button
            @click="activeTab = 'paste'"
            :class="[
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
              activeTab === 'paste'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
          >
            Paste Output
          </button>
          <button
            @click="activeTab = 'file'"
            :class="[
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
              activeTab === 'file'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            ]"
          >
            Upload File
          </button>
        </div>

        <!-- Paste tab -->
        <div v-if="activeTab === 'paste'">
          <textarea
            v-model="uploadText"
            placeholder="Paste the output from your AI tool here..."
            class="w-full min-h-[200px] border border-gray-300 rounded-lg p-3 font-mono text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus:border-blue-500 transition"
          ></textarea>
        </div>

        <!-- File tab -->
        <div v-if="activeTab === 'file'" class="border border-dashed border-gray-300 rounded-lg p-6 text-center">
          <input
            ref="fileInput"
            type="file"
            accept=".txt,.md,.json"
            class="hidden"
            @change="handleFileChange"
          />
          <button
            @click="fileInput?.click()"
            class="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm rounded-lg cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors duration-200"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            Choose file (.txt, .md, .json)
          </button>
          <p v-if="selectedFilename" class="mt-2 text-sm text-gray-600 font-mono">{{ selectedFilename }}</p>
          <p v-else class="mt-2 text-xs text-gray-400">No file selected</p>
        </div>
      </div>

      <!-- Character count -->
      <div class="mb-3 flex items-center gap-2">
        <span class="text-xs text-gray-500">{{ uploadText.length.toLocaleString() }} characters</span>
        <span v-if="uploadText.length > 95000" class="text-xs font-medium text-amber-600">
          Approaching 100KB limit
        </span>
      </div>

      <!-- Upload button -->
      <button
        @click="handleUpload"
        :disabled="uploadText.trim().length < 10 || isUploading"
        class="inline-flex items-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white text-sm font-medium rounded-lg disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 transition-colors duration-200"
      >
        <svg v-if="isUploading" class="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>{{ isUploading ? 'Uploading...' : 'Upload &amp; Analyze' }}</span>
      </button>
    </div>

    <!-- Status section (analysis in progress) -->
    <div v-else-if="codeAnalysis && codeAnalysis.status !== 'completed'">
      <div class="flex items-center gap-3 mb-2">
        <span :class="statusPillClass">{{ codeAnalysis.status }}</span>
        <p class="text-sm text-gray-700">{{ statusMessage }}</p>
      </div>
      <p v-if="isPolling" class="text-xs text-gray-400">Checking for updates...</p>
    </div>

    <!-- Results section (completed) -->
    <div v-else-if="codeAnalysis && codeAnalysis.status === 'completed'">
      <!-- Framework badge -->
      <div v-if="codeAnalysis.detected_framework" class="mb-3">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
          Detected framework: {{ codeAnalysis.detected_framework }}
        </span>
      </div>

      <!-- Summary stat -->
      <p class="text-sm font-medium text-gray-700 mb-4">
        {{ recommendations.length }} code issue{{ recommendations.length !== 1 ? 's' : '' }} found
      </p>

      <!-- Empty state -->
      <div v-if="recommendations.length === 0" class="text-sm text-gray-500 italic">
        No specific code issues found. Your implementation looks solid in the analyzed areas.
      </div>

      <!-- Grouped by severity -->
      <div v-else class="space-y-6">
        <!-- High severity -->
        <div v-if="highRecs.length > 0">
          <div class="flex items-center gap-2 mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-red-700">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <h6 class="text-sm font-semibold text-red-700">High Severity ({{ highRecs.length }})</h6>
          </div>
          <div class="space-y-3">
            <CodeRecommendationCard
              v-for="rec in highRecs"
              :key="rec.id"
              :rec="rec"
              @status-change="handleStatusChange"
            />
          </div>
        </div>

        <!-- Medium severity -->
        <div v-if="mediumRecs.length > 0">
          <div class="flex items-center gap-2 mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-amber-600">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <h6 class="text-sm font-semibold text-amber-600">Medium Severity ({{ mediumRecs.length }})</h6>
          </div>
          <div class="space-y-3">
            <CodeRecommendationCard
              v-for="rec in mediumRecs"
              :key="rec.id"
              :rec="rec"
              @status-change="handleStatusChange"
            />
          </div>
        </div>

        <!-- Low severity -->
        <div v-if="lowRecs.length > 0">
          <div class="flex items-center gap-2 mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-blue-600">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
            <h6 class="text-sm font-semibold text-blue-600">Low Severity ({{ lowRecs.length }})</h6>
          </div>
          <div class="space-y-3">
            <CodeRecommendationCard
              v-for="rec in lowRecs"
              :key="rec.id"
              :rec="rec"
              @status-change="handleStatusChange"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  auditId: string
}>()

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

const { isUploading, isPolling, codeAnalysis, recommendations, error, uploadOutput } =
  useCodeAnalysis(computed(() => props.auditId))

// ---------------------------------------------------------------------------
// Local state
// ---------------------------------------------------------------------------

const CATEGORIES = [
  { value: 'crawlability', label: 'Crawlability' },
  { value: 'content_structure', label: 'Content Structure' },
  { value: 'structured_data', label: 'Structured Data' },
  { value: 'authority', label: 'Authority & SEO' },
]

const activeTab = ref<'paste' | 'file'>('paste')
const uploadText = ref('')
const selectedCategories = ref<string[]>([])
const selectedFilename = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

// ---------------------------------------------------------------------------
// File handling
// ---------------------------------------------------------------------------

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  selectedFilename.value = file.name
  const reader = new FileReader()
  reader.onload = (e) => {
    uploadText.value = (e.target?.result as string) || ''
  }
  reader.readAsText(file)
}

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

function handleUpload() {
  uploadOutput(uploadText.value, selectedCategories.value)
}

// ---------------------------------------------------------------------------
// Status display
// ---------------------------------------------------------------------------

const statusPillClass = computed(() => {
  const status = codeAnalysis.value?.status
  const base = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize'
  if (status === 'pending') return `${base} bg-gray-100 text-gray-700`
  if (status === 'parsing') return `${base} bg-blue-100 text-blue-700 animate-pulse`
  if (status === 'recommending') return `${base} bg-amber-100 text-amber-700 animate-pulse`
  if (status === 'failed') return `${base} bg-red-100 text-red-700`
  return `${base} bg-gray-100 text-gray-700`
})

const statusMessage = computed(() => {
  switch (codeAnalysis.value?.status) {
    case 'pending':
      return 'Upload received. Starting analysis...'
    case 'parsing':
      return 'Parsing your AI tool output...'
    case 'recommending':
      return 'Generating code-specific recommendations...'
    case 'failed':
      return `Analysis failed: ${codeAnalysis.value?.error_message || 'Unknown error'}`
    default:
      return ''
  }
})

// ---------------------------------------------------------------------------
// Grouped recommendations
// ---------------------------------------------------------------------------

const highRecs = computed(() => recommendations.value.filter((r) => r.severity === 'high'))
const mediumRecs = computed(() => recommendations.value.filter((r) => r.severity === 'medium'))
const lowRecs = computed(() => recommendations.value.filter((r) => r.severity === 'low'))

// ---------------------------------------------------------------------------
// Status update
// ---------------------------------------------------------------------------

async function handleStatusChange({ id, status }: { id: string; status: string }) {
  try {
    await useApiFetch(`/code-analysis/${props.auditId}/recommendations/${id}`, {
      method: 'PATCH',
      body: { status },
    })
    const rec = recommendations.value.find((r) => r.id === id)
    if (rec) rec.status = status
  } catch {
    // Silently fail — status update is non-critical
  }
}
</script>
