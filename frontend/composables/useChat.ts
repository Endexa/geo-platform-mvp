import { ref, type Ref } from 'vue'
import { fetchEventSource } from '@microsoft/fetch-event-source'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export function useChat(auditId: Ref<string>) {
  const config = useRuntimeConfig()

  const messages = ref<ChatMessage[]>([])
  const streamingContent = ref('')
  const isStreaming = ref(false)
  const error = ref<string | null>(null)
  const abortController = ref<AbortController | null>(null)

  function getToken(): string | null {
    if (import.meta.server) return null
    const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]*)/)
    return match ? decodeURIComponent(match[1]) : null
  }

  async function loadHistory() {
    try {
      const data = await useApiFetch<{ messages: Array<{ role: string; content: string; timestamp: string }>; audit_id: string }>(
        `/chat/${auditId.value}/history`
      )
      if (data.messages && data.messages.length > 0) {
        messages.value = data.messages.map((m) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: m.timestamp,
        }))
      }
    } catch {
      // No history yet is fine -- silently ignore
    }
  }

  async function sendMessage(content: string) {
    if (isStreaming.value || !content.trim()) return

    // Push user message immediately (optimistic UI)
    messages.value.push({
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    })

    error.value = null
    streamingContent.value = ''
    isStreaming.value = true
    abortController.value = new AbortController()

    const token = getToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    try {
      await fetchEventSource(
        `${config.public.apiUrl}/api/v1/chat/${auditId.value}/chat`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ message: content.trim() }),
          signal: abortController.value.signal,
          onmessage(ev) {
            try {
              const data = JSON.parse(ev.data)
              if (data.token) {
                streamingContent.value += data.token
              } else if (data.done) {
                messages.value.push({
                  role: 'assistant',
                  content: data.full_response || streamingContent.value,
                  timestamp: new Date().toISOString(),
                })
                streamingContent.value = ''
                isStreaming.value = false
              } else if (data.error) {
                error.value = data.error
                isStreaming.value = false
              }
            } catch {
              // Ignore unparseable events
            }
          },
          onerror(err) {
            error.value = 'Connection lost. Please try again.'
            isStreaming.value = false
            throw err // stop retrying
          },
          openWhenHidden: true,
        }
      )
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        // User stopped -- ignore
        return
      }
      if (!error.value) {
        error.value = 'Failed to send message. Please try again.'
      }
      isStreaming.value = false
    }
  }

  function stopStreaming() {
    if (abortController.value) {
      abortController.value.abort()
    }
    if (streamingContent.value) {
      messages.value.push({
        role: 'assistant',
        content: streamingContent.value + ' [Response stopped]',
        timestamp: new Date().toISOString(),
      })
    }
    streamingContent.value = ''
    isStreaming.value = false
  }

  return {
    messages,
    streamingContent,
    isStreaming,
    error,
    sendMessage,
    stopStreaming,
    loadHistory,
  }
}
