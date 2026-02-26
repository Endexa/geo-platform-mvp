<template>
  <Teleport to="body">
    <!-- Overlay backdrop -->
    <div
      v-if="isOpen"
      class="fixed inset-0 bg-black/30 z-40 transition-opacity duration-200"
      @click="$emit('close')"
    />

    <!-- Panel -->
    <div
      class="fixed top-0 right-0 h-full w-96 bg-white shadow-xl z-40 flex flex-col transition-transform duration-200"
      :class="isOpen ? 'translate-x-0' : 'translate-x-full'"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <h3 class="text-base font-semibold text-slate-800" style="font-family: 'Fira Code', monospace;">
          Ask about your audit
        </h3>
        <button
          @click="$emit('close')"
          class="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors duration-200"
          aria-label="Close chat panel"
        >
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>

      <!-- Message list -->
      <div ref="messageListRef" class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        <!-- Empty state -->
        <div v-if="messages.length === 0 && !isStreaming" class="text-center py-8">
          <p class="text-sm text-slate-500" style="font-family: 'Fira Sans', sans-serif;">
            Ask me anything about your audit. For example:
          </p>
          <div class="mt-3 space-y-2">
            <p class="text-sm text-blue-700 italic">"Why is my schema score low?"</p>
            <p class="text-sm text-blue-700 italic">"What should I fix first?"</p>
            <p class="text-sm text-blue-700 italic">"How can I improve crawlability?"</p>
          </div>
        </div>

        <!-- Messages -->
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[80%] rounded-lg px-3 py-2 text-sm"
            :class="msg.role === 'user'
              ? 'bg-primary-800 text-white'
              : 'bg-slate-50 text-slate-800 border border-slate-200'"
            style="font-family: 'Fira Sans', sans-serif;"
          >
            <div class="whitespace-pre-wrap break-words">{{ msg.content }}</div>
          </div>
        </div>

        <!-- Streaming bubble -->
        <div v-if="isStreaming && streamingContent" class="flex justify-start">
          <div
            class="max-w-[80%] rounded-lg px-3 py-2 text-sm bg-slate-50 text-slate-800 border border-slate-200"
            style="font-family: 'Fira Sans', sans-serif;"
          >
            <div class="whitespace-pre-wrap break-words">
              {{ streamingContent }}<span class="inline-block w-1.5 h-4 bg-blue-600 ml-0.5 animate-pulse align-text-bottom" />
            </div>
          </div>
        </div>

        <!-- Streaming indicator (no content yet) -->
        <div v-else-if="isStreaming" class="flex justify-start">
          <div class="rounded-lg px-3 py-2 text-sm bg-slate-50 border border-slate-200">
            <div class="flex items-center gap-1">
              <span class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms;" />
              <span class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms;" />
              <span class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms;" />
            </div>
          </div>
        </div>

        <!-- Scroll anchor -->
        <div ref="scrollAnchorRef" />
      </div>

      <!-- Error banner -->
      <div v-if="error" class="px-4 py-2 bg-red-50 border-t border-red-200">
        <p class="text-xs text-red-700">{{ error }}</p>
      </div>

      <!-- Input area -->
      <div class="border-t border-slate-200 px-4 py-3">
        <div class="flex items-center gap-2">
          <input
            v-model="inputText"
            type="text"
            placeholder="Ask about your audit results..."
            class="flex-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none transition-colors duration-200"
            style="font-family: 'Fira Sans', sans-serif;"
            @keydown.enter.prevent="handleSend"
            :disabled="isStreaming"
          />
          <button
            v-if="isStreaming"
            @click="stopStreaming"
            class="p-2 rounded-lg bg-red-500 text-white hover:bg-red-600 cursor-pointer focus-visible:ring-2 focus-visible:ring-red-400 transition-colors duration-200"
            aria-label="Stop response"
          >
            <StopCircleIcon class="w-5 h-5" />
          </button>
          <button
            v-else
            @click="handleSend"
            :disabled="!inputText.trim()"
            class="p-2 rounded-lg bg-blue-800 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors duration-200"
            aria-label="Send message"
          >
            <PaperAirplaneIcon class="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { XMarkIcon, PaperAirplaneIcon, StopCircleIcon } from '@heroicons/vue/24/solid'

const props = defineProps<{
  auditId: string
  isOpen: boolean
}>()

defineEmits<{
  close: []
}>()

const auditIdRef = computed(() => props.auditId)
const { messages, streamingContent, isStreaming, error, sendMessage, stopStreaming, loadHistory } = useChat(auditIdRef)

const inputText = ref('')
const messageListRef = ref<HTMLElement | null>(null)
const scrollAnchorRef = ref<HTMLElement | null>(null)

function handleSend() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return
  inputText.value = ''
  sendMessage(text)
}

// Load history when panel opens
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      loadHistory()
    }
  }
)

// Auto-scroll to bottom on new messages or streaming content
watch(
  [() => messages.value.length, streamingContent],
  () => {
    nextTick(() => {
      scrollAnchorRef.value?.scrollIntoView({ behavior: 'smooth' })
    })
  }
)
</script>
