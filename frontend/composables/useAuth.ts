interface User {
  id: string
  email: string
  full_name: string | null
  role: string
}

function setTokenCookie(value: string) {
  if (!import.meta.server) {
    document.cookie = `access_token=${encodeURIComponent(value)}; path=/; max-age=${30 * 60}; SameSite=Lax`
  }
}

function clearTokenCookie() {
  if (!import.meta.server) {
    document.cookie = 'access_token=; path=/; max-age=0'
  }
}

export const useAuth = () => {
  const token = useCookie('access_token')
  const user = useState<User | null>('auth_user', () => null)
  const isLoggedIn = computed(() => !!token.value)

  const login = async (email: string, password: string) => {
    const data = await useApiFetch<{ access_token: string; refresh_token?: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    token.value = data.access_token
    setTokenCookie(data.access_token)
    await fetchUser()
  }

  const register = async (email: string, password: string, fullName?: string) => {
    const data = await useApiFetch<{ access_token: string; token_type: string }>('/auth/register', {
      method: 'POST',
      body: { email, password, full_name: fullName || null },
    })
    token.value = data.access_token
    setTokenCookie(data.access_token)
    await fetchUser()
  }

  const fetchUser = async () => {
    try {
      const data = await useApiFetch<User>('/auth/me')
      user.value = data
    } catch {
      user.value = null
    }
  }

  const logout = () => {
    token.value = null
    clearTokenCookie()
    user.value = null
    navigateTo('/login')
  }

  return { token, user, isLoggedIn, login, register, logout, fetchUser }
}
