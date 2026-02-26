import { ref, onMounted } from 'vue'

export function useScrollFadeIn() {
  const el = ref<HTMLElement | null>(null)
  const visible = ref(false)

  onMounted(() => {
    if (!el.value) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          visible.value = true
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.1 }
    )
    observer.observe(el.value)
  })

  return { el, visible }
}
