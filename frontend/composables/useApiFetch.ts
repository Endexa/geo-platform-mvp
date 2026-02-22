export function useApiFetch<T>(path: string, opts: any = {}): Promise<T> {
  const config = useRuntimeConfig()
  const token = useCookie('access_token')

  return $fetch<T>(path, {
    baseURL: `${config.public.apiUrl}/api/v1`,
    headers: {
      ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
      ...opts.headers,
    },
    onResponseError({ response }) {
      if (response.status === 401) {
        token.value = null
        navigateTo('/login')
      }
    },
    ...opts,
  })
}
