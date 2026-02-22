<template>
  <div class="space-y-4">
    <!-- Section Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <h3 class="text-lg font-semibold text-gray-900">Queries</h3>
        <span class="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
          {{ queries.length }}
        </span>
      </div>
      <button
        v-if="!showAddForm"
        type="button"
        class="inline-flex items-center space-x-1.5 px-3 py-1.5 text-sm font-medium text-primary-700 bg-primary-50 rounded-lg hover:bg-primary-100 cursor-pointer transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
        @click="showAddForm = true"
      >
        <PlusIcon class="w-4 h-4" />
        <span>Add Custom Query</span>
      </button>
    </div>

    <!-- Add Custom Query Form -->
    <div v-if="showAddForm" class="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-3">
      <p class="text-sm font-medium text-amber-800">New Custom Query</p>
      <div>
        <input
          v-model="newQueryText"
          type="text"
          placeholder="e.g., What are the best tools for..."
          class="w-full px-3 py-2 border border-amber-300 rounded-lg text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus:border-primary-500 bg-white"
          @keyup.enter="addQuery"
        />
        <p v-if="newQueryError" class="mt-1 text-xs text-red-600">{{ newQueryError }}</p>
      </div>
      <div>
        <select
          v-model="newQueryCategory"
          class="px-3 py-2 border border-amber-300 rounded-lg text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus:border-primary-500 bg-white cursor-pointer"
        >
          <option v-for="cat in categories" :key="cat.value" :value="cat.value">
            {{ cat.label }}
          </option>
        </select>
      </div>
      <div class="flex space-x-2">
        <button
          type="button"
          class="px-4 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          :disabled="!isNewQueryValid || saving"
          @click="addQuery"
        >
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
        <button
          type="button"
          class="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          @click="cancelAdd"
        >
          Cancel
        </button>
      </div>
    </div>

    <!-- API Error -->
    <div v-if="apiError" class="bg-red-50 border border-red-200 rounded-lg p-3">
      <p class="text-sm text-red-700">{{ apiError }}</p>
    </div>

    <!-- Query List -->
    <div class="space-y-2">
      <div
        v-for="query in sortedQueries"
        :key="query.id"
        class="rounded-lg border p-4"
        :class="query.is_custom
          ? 'bg-amber-50 border-amber-200 border-dashed'
          : 'bg-white border-gray-200'"
      >
        <!-- View Mode -->
        <div v-if="editingId !== query.id" class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-2 mb-1">
              <span
                class="text-xs font-medium uppercase tracking-wide rounded px-2 py-0.5"
                :class="categoryColor(query.category)"
              >{{ query.category }}</span>
              <span
                v-if="query.is_custom"
                class="text-xs font-medium text-amber-700 bg-amber-100 rounded px-2 py-0.5"
              >Custom</span>
            </div>
            <p class="text-sm text-gray-900">{{ query.query_text }}</p>
          </div>
          <div v-if="query.is_custom" class="flex items-center space-x-1 ml-3 flex-shrink-0">
            <button
              type="button"
              class="p-1.5 text-gray-400 hover:text-primary-600 rounded cursor-pointer transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500"
              title="Edit query"
              @click="startEdit(query)"
            >
              <PencilIcon class="w-4 h-4" />
            </button>
            <button
              type="button"
              class="p-1.5 text-gray-400 hover:text-red-600 rounded cursor-pointer transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500"
              title="Delete query"
              @click="confirmDelete(query)"
            >
              <TrashIcon class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Edit Mode -->
        <div v-else class="space-y-3">
          <div>
            <input
              v-model="editQueryText"
              type="text"
              class="w-full px-3 py-2 border border-amber-300 rounded-lg text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus:border-primary-500 bg-white"
            />
            <p v-if="editQueryError" class="mt-1 text-xs text-red-600">{{ editQueryError }}</p>
          </div>
          <div>
            <select
              v-model="editQueryCategory"
              class="px-3 py-2 border border-amber-300 rounded-lg text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus:border-primary-500 bg-white cursor-pointer"
            >
              <option v-for="cat in categories" :key="cat.value" :value="cat.value">
                {{ cat.label }}
              </option>
            </select>
          </div>
          <div class="flex space-x-2">
            <button
              type="button"
              class="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
              :disabled="!isEditValid || saving"
              @click="saveEdit"
            >
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
            <button
              type="button"
              class="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
              @click="cancelEdit"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 z-30 flex items-center justify-center bg-black/30"
      @click.self="deleteTarget = null"
    >
      <div class="bg-white rounded-lg border border-gray-200 p-6 max-w-sm mx-4 shadow-lg">
        <p class="text-sm font-medium text-gray-900 mb-2">Delete custom query?</p>
        <p class="text-sm text-gray-600 mb-4 break-words">"{{ deleteTarget.query_text }}"</p>
        <div class="flex justify-end space-x-2">
          <button
            type="button"
            class="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            @click="deleteTarget = null"
          >
            Cancel
          </button>
          <button
            type="button"
            class="px-4 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            :disabled="saving"
            @click="executeDelete"
          >
            {{ saving ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/vue/24/outline'

interface QueryItem {
  id: string
  query_text: string
  category: string
  is_custom: boolean
  sort_order?: number
  engine_responses?: Array<unknown>
}

const props = defineProps<{
  auditId: string
  queries: QueryItem[]
}>()

const emit = defineEmits<{
  'query-added': []
  'query-updated': []
  'query-deleted': []
}>()

const categories = [
  { value: 'custom', label: 'Custom' },
  { value: 'industry', label: 'Industry' },
  { value: 'brand_direct', label: 'Brand Direct' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'problem', label: 'Problem' },
  { value: 'recommendation', label: 'Recommendation' },
]

// State
const showAddForm = ref(false)
const newQueryText = ref('')
const newQueryCategory = ref('custom')
const newQueryError = ref('')
const editingId = ref<string | null>(null)
const editQueryText = ref('')
const editQueryCategory = ref('')
const editQueryError = ref('')
const deleteTarget = ref<QueryItem | null>(null)
const saving = ref(false)
const apiError = ref('')

const sortedQueries = computed(() => {
  return [...props.queries].sort((a, b) => {
    // Custom queries first, then by sort_order
    if (a.is_custom !== b.is_custom) return a.is_custom ? -1 : 1
    return (a.sort_order ?? 0) - (b.sort_order ?? 0)
  })
})

const isNewQueryValid = computed(() => {
  return newQueryText.value.length >= 10 && newQueryText.value.length <= 500
})

const isEditValid = computed(() => {
  return editQueryText.value.length >= 10 && editQueryText.value.length <= 500
})

// Watchers for inline validation
watch(newQueryText, (val) => {
  if (val.length > 0 && val.length < 10) {
    newQueryError.value = 'Query must be at least 10 characters'
  } else if (val.length > 500) {
    newQueryError.value = 'Query must be at most 500 characters'
  } else {
    newQueryError.value = ''
  }
})

watch(editQueryText, (val) => {
  if (val.length > 0 && val.length < 10) {
    editQueryError.value = 'Query must be at least 10 characters'
  } else if (val.length > 500) {
    editQueryError.value = 'Query must be at most 500 characters'
  } else {
    editQueryError.value = ''
  }
})

function categoryColor(category: string): string {
  const colors: Record<string, string> = {
    industry: 'text-blue-700 bg-blue-100',
    brand_direct: 'text-purple-700 bg-purple-100',
    comparison: 'text-orange-700 bg-orange-100',
    problem: 'text-red-700 bg-red-100',
    recommendation: 'text-green-700 bg-green-100',
    custom: 'text-amber-700 bg-amber-100',
  }
  return colors[category] || 'text-gray-700 bg-gray-100'
}

// CRUD operations

async function addQuery() {
  if (!isNewQueryValid.value || saving.value) return
  saving.value = true
  apiError.value = ''

  try {
    await useApiFetch(`/audit/${props.auditId}/queries`, {
      method: 'POST',
      body: {
        query_text: newQueryText.value,
        category: newQueryCategory.value,
      },
    })
    showAddForm.value = false
    newQueryText.value = ''
    newQueryCategory.value = 'custom'
    emit('query-added')
  } catch (err: any) {
    apiError.value = err.data?.detail || err.message || 'Failed to add query'
  } finally {
    saving.value = false
  }
}

function cancelAdd() {
  showAddForm.value = false
  newQueryText.value = ''
  newQueryCategory.value = 'custom'
  newQueryError.value = ''
}

function startEdit(query: QueryItem) {
  editingId.value = query.id
  editQueryText.value = query.query_text
  editQueryCategory.value = query.category
  editQueryError.value = ''
}

function cancelEdit() {
  editingId.value = null
  editQueryText.value = ''
  editQueryCategory.value = ''
  editQueryError.value = ''
}

async function saveEdit() {
  if (!isEditValid.value || !editingId.value || saving.value) return
  saving.value = true
  apiError.value = ''

  try {
    await useApiFetch(`/audit/${props.auditId}/queries/${editingId.value}`, {
      method: 'PUT',
      body: {
        query_text: editQueryText.value,
        category: editQueryCategory.value,
      },
    })
    editingId.value = null
    emit('query-updated')
  } catch (err: any) {
    const detail = err.data?.detail || err.message || 'Failed to update query'
    if (err.status === 403) {
      apiError.value = 'Only custom queries can be edited'
    } else {
      apiError.value = detail
    }
  } finally {
    saving.value = false
  }
}

function confirmDelete(query: QueryItem) {
  deleteTarget.value = query
}

async function executeDelete() {
  if (!deleteTarget.value || saving.value) return
  saving.value = true
  apiError.value = ''

  try {
    await useApiFetch(`/audit/${props.auditId}/queries/${deleteTarget.value.id}`, {
      method: 'DELETE',
    })
    deleteTarget.value = null
    emit('query-deleted')
  } catch (err: any) {
    const detail = err.data?.detail || err.message || 'Failed to delete query'
    if (err.status === 403) {
      apiError.value = 'Only custom queries can be deleted'
    } else if (err.status === 409) {
      apiError.value = detail
    } else {
      apiError.value = detail
    }
    deleteTarget.value = null
  } finally {
    saving.value = false
  }
}
</script>
