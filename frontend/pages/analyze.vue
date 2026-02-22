<template>
  <div class="max-w-4xl mx-auto space-y-6">
      <!-- Header -->
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Analyze Website</h1>
        <p class="text-gray-600 mt-1">Get instant GEO insights for any URL</p>
      </div>

      <!-- Input Form -->
      <div class="card">
        <form @submit.prevent="startAnalysis" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Website URL
            </label>
            <input
              v-model="url"
              type="url"
              required
              placeholder="https://example.com"
              class="input-field"
              :disabled="analyzing"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Target Keywords (comma separated)
            </label>
            <input
              v-model="keywordsInput"
              type="text"
              placeholder="AI search, optimization, visibility"
              class="input-field"
              :disabled="analyzing"
            />
          </div>

          <button
            type="submit"
            class="btn-primary w-full py-3"
            :disabled="analyzing"
          >
            <span v-if="!analyzing">Analyze Now</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Analyzing...
            </span>
          </button>
        </form>
      </div>

      <!-- Progress Stepper -->
      <div v-if="analyzing" class="card">
        <h3 class="font-semibold text-gray-900 mb-4">Analysis Progress</h3>
        <div class="space-y-4">
          <div v-for="(step, index) in steps" :key="index" class="flex items-center">
            <div class="flex-shrink-0">
              <div v-if="currentStep > index" class="w-8 h-8 bg-success-500 rounded-full flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div v-else-if="currentStep === index" class="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
                <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <div v-else class="w-8 h-8 bg-gray-200 rounded-full"></div>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium" :class="currentStep >= index ? 'text-gray-900' : 'text-gray-500'">
                {{ step }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Results -->
      <div v-if="results" class="space-y-6">
        <!-- Score Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="card">
            <p class="text-sm text-gray-600">GEO Score</p>
            <p class="text-3xl font-bold mt-2" :class="getScoreColor(results.geo_score)">
              {{ results.geo_score }}
            </p>
          </div>
          <div class="card">
            <p class="text-sm text-gray-600">Visibility</p>
            <p class="text-3xl font-bold text-primary-600 mt-2">
              {{ results.visibility_score }}
            </p>
          </div>
          <div class="card">
            <p class="text-sm text-gray-600">Readability</p>
            <p class="text-3xl font-bold text-primary-600 mt-2">
              {{ results.readability_score }}
            </p>
          </div>
          <div class="card">
            <p class="text-sm text-gray-600">Authority</p>
            <p class="text-3xl font-bold text-primary-600 mt-2">
              {{ results.authority_score }}
            </p>
          </div>
        </div>

        <!-- Actions -->
        <div class="card">
          <h3 class="font-semibold text-gray-900 mb-4">Next Steps</h3>
          <div class="flex gap-4">
            <button @click="generateRecommendations" class="btn-primary">
              Generate Recommendations
            </button>
            <button @click="resetForm" class="btn-secondary">
              Analyze Another URL
            </button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })
const config = useRuntimeConfig()
const url = ref('')
const keywordsInput = ref('')
const analyzing = ref(false)
const currentStep = ref(0)
const results = ref(null)

const steps = [
  'Crawling Site...',
  'Simulating AI Search...',
  'Calculating Vectors...',
  'Done!'
]

const startAnalysis = async () => {
  analyzing.value = true
  currentStep.value = 0
  results.value = null

  try {
    const keywords = keywordsInput.value.split(',').map(k => k.trim()).filter(k => k)

    // Step 1: Initiate analysis
    const response = await fetch(`${config.public.apiUrl}/api/v1/analysis/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url.value, keywords })
    })

    if (!response.ok) {
      const errorData = await response.json()
      console.error('Analysis API error:', errorData)
      throw new Error(errorData.detail || 'Failed to start analysis')
    }

    const data = await response.json()
    const analysisId = data.analysis_id

    if (!analysisId) {
      throw new Error('No analysis ID returned from server')
    }

    // Step 2-4: Poll for results
    let pollAttempts = 0
    const maxPollAttempts = 30  // 1 minute max
    const pollInterval = setInterval(async () => {
      pollAttempts++
      currentStep.value = Math.min(currentStep.value + 1, steps.length - 1)

      try {
        const statusResponse = await fetch(`${config.public.apiUrl}/api/v1/analysis/${analysisId}`)
        if (!statusResponse.ok) {
          throw new Error('Failed to fetch analysis status')
        }

        const statusData = await statusResponse.json()

        if (statusData.status === 'completed') {
          clearInterval(pollInterval)
          currentStep.value = steps.length
          results.value = statusData
          analyzing.value = false
        } else if (statusData.status === 'failed') {
          clearInterval(pollInterval)
          alert('Analysis failed. Please try again.')
          analyzing.value = false
        } else if (pollAttempts >= maxPollAttempts) {
          clearInterval(pollInterval)
          alert('Analysis timeout. Please try again.')
          analyzing.value = false
        }
      } catch (pollError) {
        console.error('Polling error:', pollError)
        clearInterval(pollInterval)
        alert('Error checking analysis status')
        analyzing.value = false
      }
    }, 2000)

  } catch (error) {
    console.error('Analysis error:', error)
    alert(error.message || 'Failed to start analysis')
    analyzing.value = false
  }
}

const generateRecommendations = () => {
  navigateTo('/optimization')
}

const resetForm = () => {
  url.value = ''
  keywordsInput.value = ''
  results.value = null
  currentStep.value = 0
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-success-600'
  if (score >= 50) return 'text-warning-600'
  return 'text-danger-600'
}
</script>
