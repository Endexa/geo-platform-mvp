<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center p-4">
    <div class="max-w-md w-full">
      <!-- Card -->
      <div class="bg-white rounded-2xl shadow-2xl p-8">
        <!-- Logo -->
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-primary-600">GEO Platform</h1>
          <p class="text-gray-600 mt-2">Generative Engine Optimization</p>
        </div>

        <!-- Error Message -->
        <div v-if="errorMessage" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p class="text-sm text-red-700">{{ errorMessage }}</p>
        </div>

        <!-- Login Form -->
        <form v-if="mode === 'login'" @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label for="login-email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              id="login-email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              placeholder="you@example.com"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent focus-visible:ring-2 focus-visible:ring-primary-500"
            />
          </div>
          <div>
            <label for="login-password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              id="login-password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              placeholder="Enter your password"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent focus-visible:ring-2 focus-visible:ring-primary-500"
            />
          </div>
          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-primary-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-primary-700 transition-colors shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>

        <!-- Register Form -->
        <form v-else @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label for="register-email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              id="register-email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              placeholder="you@example.com"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent focus-visible:ring-2 focus-visible:ring-primary-500"
            />
          </div>
          <div>
            <label for="register-fullname" class="block text-sm font-medium text-gray-700 mb-1">Full Name <span class="text-gray-400">(optional)</span></label>
            <input
              id="register-fullname"
              v-model="fullName"
              type="text"
              autocomplete="name"
              placeholder="Jane Doe"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent focus-visible:ring-2 focus-visible:ring-primary-500"
            />
          </div>
          <div>
            <label for="register-password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              id="register-password"
              v-model="password"
              type="password"
              required
              autocomplete="new-password"
              placeholder="Min 12 chars, upper + lower + digit + special"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent focus-visible:ring-2 focus-visible:ring-primary-500"
            />
          </div>
          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-primary-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-primary-700 transition-colors shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {{ loading ? 'Creating account...' : 'Create Account' }}
          </button>
        </form>

        <!-- Toggle Mode -->
        <div class="mt-6 text-center">
          <button
            @click="toggleMode"
            class="text-sm text-primary-600 hover:text-primary-800 font-medium cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded"
          >
            {{ mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in' }}
          </button>
        </div>

        <!-- Features List -->
        <div class="mt-8 space-y-3">
          <div class="flex items-start">
            <svg class="w-5 h-5 text-success-600 mt-0.5 mr-2 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="text-sm text-gray-600">AI-powered GEO analysis</span>
          </div>
          <div class="flex items-start">
            <svg class="w-5 h-5 text-success-600 mt-0.5 mr-2 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="text-sm text-gray-600">Optimization recommendations</span>
          </div>
          <div class="flex items-start">
            <svg class="w-5 h-5 text-success-600 mt-0.5 mr-2 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="text-sm text-gray-600">Brand voice consistency checker</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="mt-8 text-center text-xs text-gray-500">
          <p>GEO Platform v1.0.0</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const { login, register, isLoggedIn } = useAuth()

// Redirect if already authenticated
if (isLoggedIn.value) {
  navigateTo('/audit')
}

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const fullName = ref('')
const loading = ref(false)
const errorMessage = ref('')

const toggleMode = () => {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  errorMessage.value = ''
}

const parseApiError = (error: any): string => {
  const data = error?.data || error?.response?._data
  if (data?.detail) {
    if (typeof data.detail === 'string') {
      return data.detail
    }
    if (Array.isArray(data.detail)) {
      return data.detail.map((e: any) => e.msg || e.message || String(e)).join('. ')
    }
  }
  return error?.message || 'An unexpected error occurred. Please try again.'
}

const handleLogin = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    await login(email.value, password.value)
    await navigateTo('/audit')
  } catch (error: any) {
    errorMessage.value = parseApiError(error)
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    await register(email.value, password.value, fullName.value || undefined)
    await navigateTo('/audit')
  } catch (error: any) {
    errorMessage.value = parseApiError(error)
  } finally {
    loading.value = false
  }
}
</script>
