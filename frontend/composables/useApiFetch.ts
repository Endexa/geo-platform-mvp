export function useApiFetch<T>(path: string, opts: any = {}): Promise<T> {
  const config = useRuntimeConfig()

  // Read token directly from cookie — avoids useCookie composable context issues
  function getToken(): string | null {
    if (import.meta.server) return null
    const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]*)/)
    return match ? decodeURIComponent(match[1]) : null
  }

  const { onRequest: userOnRequest, onResponseError: userOnResponseError, ...restOpts } = opts

  return $fetch<T>(path, {
    baseURL: `${config.public.apiUrl}/api/v1`,
    onRequest(ctx) {
      const token = getToken()
      if (token) {
        ctx.options.headers = {
          ...(ctx.options.headers || {}),
          Authorization: `Bearer ${token}`,
        }
      }
      userOnRequest?.(ctx)
    },
    onResponseError(ctx) {
      if (ctx.response.status === 401) {
        // Clear the cookie
        if (!import.meta.server) {
          document.cookie = 'access_token=; path=/; max-age=0'
        }
        navigateTo('/login')
      }
      userOnResponseError?.(ctx)
    },
    ...restOpts,
  })
}
