interface BrandOverview {
  brand_id: string
  brand_name: string
  domain: string
  total_audits: number
  latest_score: number | null
}

export function useBrandSelector() {
  const selectedBrandId = useState<string | null>('selectedBrandId', () => null)
  const brands = useState<BrandOverview[]>('brands', () => [])
  const brandsLoading = ref(false)
  const brandsError = ref<string | null>(null)

  async function loadBrands() {
    brandsLoading.value = true
    brandsError.value = null
    try {
      const data = await useApiFetch<{ brands: BrandOverview[]; total_brands: number }>('/brands/overview')
      brands.value = data.brands
      // Auto-select first brand if none selected
      if (!selectedBrandId.value && data.brands.length > 0) {
        selectedBrandId.value = data.brands[0].brand_id
      }
    } catch (e: any) {
      brandsError.value = e?.message || 'Failed to load brands'
    } finally {
      brandsLoading.value = false
    }
  }

  const selectedBrand = computed(() =>
    brands.value.find(b => b.brand_id === selectedBrandId.value) || null,
  )

  function selectBrand(brandId: string | null) {
    selectedBrandId.value = brandId
  }

  return {
    selectedBrandId,
    brands,
    selectedBrand,
    brandsLoading,
    brandsError,
    loadBrands,
    selectBrand,
  }
}
