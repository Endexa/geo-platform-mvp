<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Brands</h1>
        <p class="text-sm text-gray-500">Manage brands and compare GEO performance</p>
      </div>
      <button
        @click="showCreateForm = true"
        class="inline-flex items-center px-4 py-2 bg-primary-800 text-white rounded-lg text-sm font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
      >
        <PlusIcon class="w-4 h-4 mr-2" />
        Create Brand
      </button>
    </div>

    <!-- Create/Edit form modal -->
    <div
      v-if="showCreateForm"
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
    >
      <h3 class="text-lg font-semibold text-gray-900 mb-4">
        {{ editingBrand ? 'Edit Brand' : 'Create Brand' }}
      </h3>
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label for="brand-name" class="block text-sm font-medium text-gray-700 mb-1">Brand Name</label>
          <input
            id="brand-name"
            v-model="formData.name"
            type="text"
            required
            placeholder="My Brand"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:border-primary-800 outline-none"
          />
        </div>
        <div>
          <label for="brand-url" class="block text-sm font-medium text-gray-700 mb-1">URL</label>
          <input
            id="brand-url"
            v-model="formData.url"
            type="url"
            required
            placeholder="https://example.com"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:border-primary-800 outline-none"
          />
        </div>
        <div>
          <label for="brand-desc" class="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
          <textarea
            id="brand-desc"
            v-model="formData.description"
            rows="2"
            placeholder="Brief description of the brand"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:border-primary-800 outline-none resize-none"
          />
        </div>
        <p v-if="formError" class="text-sm text-red-600">{{ formError }}</p>
        <div class="flex items-center gap-3">
          <button
            type="submit"
            :disabled="formSubmitting"
            class="px-4 py-2 bg-primary-800 text-white rounded-lg text-sm font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ formSubmitting ? 'Saving...' : (editingBrand ? 'Update Brand' : 'Create Brand') }}
          </button>
          <button
            type="button"
            @click="resetForm"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-gray-400"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="i in 3"
        :key="i"
        class="bg-white rounded-xl border border-gray-200 p-6 h-56 animate-pulse"
      >
        <div class="h-4 bg-gray-200 rounded w-1/2 mb-4" />
        <div class="h-3 bg-gray-200 rounded w-1/3 mb-6" />
        <div class="grid grid-cols-3 gap-3 mb-4">
          <div class="h-12 bg-gray-200 rounded" />
          <div class="h-12 bg-gray-200 rounded" />
          <div class="h-12 bg-gray-200 rounded" />
        </div>
        <div class="h-8 bg-gray-200 rounded" />
      </div>
    </div>

    <!-- Error state -->
    <div
      v-else-if="loadError"
      class="bg-white rounded-xl border border-gray-200 p-12 text-center"
    >
      <ExclamationTriangleIcon class="w-16 h-16 mx-auto text-warning-400" />
      <h2 class="text-lg font-semibold text-gray-700 mt-4">Something went wrong</h2>
      <p class="text-gray-500 mt-2 mb-6">{{ loadError }}</p>
      <button @click="loadBrands" class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2">Try Again</button>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="overviewBrands.length === 0 && !showCreateForm"
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center"
    >
      <BuildingOfficeIcon class="w-16 h-16 mx-auto text-gray-300" />
      <h2 class="text-lg font-semibold text-gray-700 mt-4">No brands yet</h2>
      <p class="text-gray-500 mt-2 mb-6">Create your first brand to start tracking multiple sites</p>
      <button
        @click="showCreateForm = true"
        class="inline-flex items-center px-6 py-3 bg-primary-800 text-white rounded-lg font-medium hover:bg-primary-900 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-800 focus-visible:ring-offset-2"
      >
        Create Brand
      </button>
    </div>

    <!-- Brand cards grid -->
    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <BrandCard
          v-for="brand in overviewBrands"
          :key="brand.brand_id"
          :brand="brand"
          @edit="handleEdit"
          @delete="handleDelete"
        />
      </div>

      <!-- Cross-brand comparison (2+ brands only) -->
      <BrandComparison
        v-if="overviewBrands.length >= 2"
        :brands="overviewBrands"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { BuildingOfficeIcon, PlusIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

definePageMeta({ layout: 'dashboard' })

interface BrandOverview {
  brand_id: string
  brand_name: string
  brand_url: string
  brand_domain: string
  latest_audit_id: string | null
  combined_geo_score: number | null
  visibility_score: number | null
  optimization_score: number | null
  mention_count: number
  top_issues_count: number
  audit_count: number
  last_audited_at: string | null
}

const loading = ref(true)
const loadError = ref('')
const overviewBrands = ref<BrandOverview[]>([])
const showCreateForm = ref(false)
const editingBrand = ref<BrandOverview | null>(null)
const formSubmitting = ref(false)
const formError = ref<string | null>(null)

const formData = ref({
  name: '',
  url: '',
  description: '',
})

// Fetch brand overview on mount
onMounted(async () => {
  await loadBrands()
})

async function loadBrands() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await useApiFetch<{ brands: BrandOverview[]; total_brands: number }>('/brands/overview')
    overviewBrands.value = data.brands
  } catch (e: any) {
    loadError.value = e.data?.detail || e.message || 'Failed to load brands'
  } finally {
    loading.value = false
  }
}

function handleEdit(brand: BrandOverview) {
  editingBrand.value = brand
  formData.value = {
    name: brand.brand_name,
    url: brand.brand_url,
    description: '',
  }
  formError.value = null
  showCreateForm.value = true
}

async function handleDelete(brandId: string) {
  try {
    await useApiFetch(`/brands/${brandId}`, { method: 'DELETE' })
    await loadBrands()
  } catch (e) {
    console.error('Failed to delete brand:', e)
  }
}

async function handleSubmit() {
  formSubmitting.value = true
  formError.value = null

  try {
    if (editingBrand.value) {
      // Update existing brand
      await useApiFetch(`/brands/${editingBrand.value.brand_id}`, {
        method: 'PUT',
        body: {
          name: formData.value.name,
          url: formData.value.url,
          description: formData.value.description || null,
        },
      })
    } else {
      // Create new brand
      await useApiFetch('/brands/', {
        method: 'POST',
        body: {
          name: formData.value.name,
          url: formData.value.url,
          description: formData.value.description || null,
        },
      })
    }

    resetForm()
    await loadBrands()
  } catch (e: any) {
    if (e?.response?.status === 409) {
      formError.value = 'A brand with this domain already exists'
    } else {
      formError.value = 'Failed to save brand. Please try again.'
    }
  } finally {
    formSubmitting.value = false
  }
}

function resetForm() {
  showCreateForm.value = false
  editingBrand.value = null
  formData.value = { name: '', url: '', description: '' }
  formError.value = null
}
</script>
