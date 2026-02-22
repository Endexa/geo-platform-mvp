<template>
  <div class="bg-white rounded-lg border border-gray-200 p-8">
    <form @submit.prevent="onSubmit" class="space-y-4">
      <div>
        <label for="audit-url" class="block text-sm font-medium text-gray-700 mb-1">Website URL</label>
        <input
          id="audit-url"
          v-model="url"
          type="url"
          placeholder="https://example.com"
          class="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus:border-primary-500"
          :disabled="loading"
        />
        <p v-if="error" class="mt-1 text-sm text-red-600">{{ error }}</p>
      </div>

      <button
        type="submit"
        :disabled="!isValid || loading"
        class="bg-primary-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-primary-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
      >
        {{ loading ? 'Starting audit...' : 'Start AI Audit' }}
      </button>

      <p class="text-sm text-gray-500">Enter a URL to analyze how AI engines see this brand</p>
    </form>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  loading?: boolean
}>(), {
  loading: false,
})

const emit = defineEmits<{
  submit: [url: string]
}>()

const url = ref('')
const error = ref('')

const isValid = computed(() => {
  return url.value.length > 0 && !error.value
})

watch(url, (val) => {
  if (!val) {
    error.value = ''
    return
  }
  if (!/^https?:\/\/.+/.test(val)) {
    error.value = 'URL must start with http:// or https://'
  } else {
    error.value = ''
  }
})

function onSubmit() {
  if (!url.value || error.value || props.loading) return
  emit('submit', url.value)
}
</script>
