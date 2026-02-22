<template>
  <div class="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
    <template v-for="(segment, i) in segments" :key="i">
      <mark
        v-if="segment.highlight"
        class="bg-yellow-200 text-yellow-900 rounded px-0.5"
        :title="`${segment.mention?.match_type} match (${segment.mention?.confidence}% confidence)`"
      >{{ segment.text }}</mark>
      <span v-else>{{ segment.text }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
interface Mention {
  char_offset: number
  matched_text: string
  match_type: string
  confidence: number
}

interface Segment {
  text: string
  highlight: boolean
  mention?: Mention
}

const props = defineProps<{
  text: string
  mentions: Mention[]
}>()

const segments = computed<Segment[]>(() => {
  if (!props.mentions.length) return [{ text: props.text, highlight: false }]

  const sorted = [...props.mentions].sort((a, b) => a.char_offset - b.char_offset)
  const result: Segment[] = []
  let cursor = 0

  for (const m of sorted) {
    // Skip overlapping mentions
    if (m.char_offset < cursor) continue

    if (m.char_offset > cursor) {
      result.push({ text: props.text.slice(cursor, m.char_offset), highlight: false })
    }
    const end = m.char_offset + m.matched_text.length
    result.push({
      text: props.text.slice(m.char_offset, end),
      highlight: true,
      mention: m,
    })
    cursor = end
  }
  if (cursor < props.text.length) {
    result.push({ text: props.text.slice(cursor), highlight: false })
  }
  return result
})
</script>
