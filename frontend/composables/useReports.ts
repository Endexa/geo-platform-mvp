/**
 * Composable for downloading audit reports and CSV exports.
 *
 * Provides methods to download PDF, HTML, and CSV files via the
 * reports API, with loading state and error handling.
 */
export const useReports = () => {
  const config = useRuntimeConfig()
  const isDownloading = ref(false)
  const downloadError = ref<string | null>(null)

  /**
   * Read the access token directly from cookie.
   */
  function getToken(): string | null {
    if (import.meta.server) return null
    const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]*)/)
    return match ? decodeURIComponent(match[1]) : null
  }

  /**
   * Generic download handler: fetches a blob and triggers browser download.
   */
  async function downloadFile(url: string, fallbackFilename: string) {
    isDownloading.value = true
    downloadError.value = null

    try {
      const token = getToken()
      const response = await $fetch.raw(url, {
        baseURL: `${config.public.apiUrl}/api/v1`,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        responseType: 'blob',
      })

      const blob = response._data as Blob
      const contentDisposition = response.headers.get('content-disposition')
      const filename =
        contentDisposition?.split('filename=')[1]?.replace(/"/g, '') ||
        fallbackFilename

      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename
      a.click()
      URL.revokeObjectURL(objectUrl)
    } catch (err: any) {
      if (err?.response?.status === 402) {
        downloadError.value = 'Upgrade to Pro to download reports'
      } else {
        downloadError.value =
          err?.data?.detail || err?.message || 'Download failed'
      }
    } finally {
      isDownloading.value = false
    }
  }

  /**
   * Download PDF audit report.
   */
  const downloadPdf = (auditId: string) =>
    downloadFile(`/reports/${auditId}/pdf`, 'report.pdf')

  /**
   * Download HTML audit report.
   */
  const downloadHtml = (auditId: string) =>
    downloadFile(`/reports/${auditId}/html`, 'report.html')

  /**
   * Download Jira-compatible CSV export.
   */
  const downloadCsv = (
    auditId: string,
    options?: { grouping?: string; epicLink?: string; fields?: string }
  ) => {
    const params = new URLSearchParams()
    if (options?.grouping) params.set('grouping', options.grouping)
    if (options?.epicLink) params.set('epic_link', options.epicLink)
    if (options?.fields) params.set('fields', options.fields)
    const qs = params.toString()
    const url = `/reports/${auditId}/csv${qs ? '?' + qs : ''}`
    return downloadFile(url, 'recommendations.csv')
  }

  return { downloadPdf, downloadHtml, downloadCsv, isDownloading, downloadError }
}
