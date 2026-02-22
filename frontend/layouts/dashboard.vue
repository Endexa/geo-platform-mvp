<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Sidebar -->
    <aside class="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 flex flex-col">
      <!-- Logo -->
      <div class="p-6 border-b border-gray-200">
        <h1 class="text-2xl font-bold text-primary-600">GEO Platform</h1>
        <p class="text-sm text-gray-500">Optimization Suite</p>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1">
        <NuxtLink
          v-for="item in navigation"
          :key="item.path"
          :to="item.path"
          class="flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors"
          :class="isActive(item.path) ? 'bg-primary-50 text-primary-700' : 'text-gray-700 hover:bg-gray-100'"
        >
          <component :is="item.icon" class="w-5 h-5 mr-3" />
          {{ item.label }}
        </NuxtLink>
      </nav>

      <!-- Upgrade CTA -->
      <div class="p-4 m-4 bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg text-white">
        <h3 class="font-semibold mb-1">Upgrade to Pro</h3>
        <p class="text-xs text-primary-100 mb-3">Unlock advanced features</p>
        <button class="w-full px-3 py-2 bg-white text-primary-600 rounded-md text-sm font-medium hover:bg-primary-50 transition-colors cursor-pointer">
          Upgrade Now
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="ml-64">
      <!-- Top Bar -->
      <header class="bg-white border-b border-gray-200 px-6 py-4">
        <div class="flex items-center justify-between">
          <!-- Breadcrumbs -->
          <div class="flex items-center space-x-2 text-sm">
            <span class="text-gray-500">Dashboard</span>
            <span class="text-gray-400">/</span>
            <span class="text-gray-900 font-medium">{{ currentPageTitle }}</span>
          </div>

          <!-- User Menu -->
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600">{{ user?.email }}</span>
            <button
              @click="logout"
              class="text-sm text-gray-500 hover:text-gray-700 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-2 py-1"
            >
              Sign Out
            </button>
            <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
              <span class="text-sm font-medium text-primary-700">{{ userInitial }}</span>
            </div>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <main class="p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  HomeIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  UsersIcon,
  LightBulbIcon,
  MicrophoneIcon,
  Cog6ToothIcon
} from '@heroicons/vue/24/outline'

const { isLoggedIn, user, logout, fetchUser } = useAuth()

// Fetch user info on mount if we have token but no user
onMounted(async () => {
  if (!isLoggedIn.value) {
    await navigateTo('/login', { replace: true })
    return
  }
  if (!user.value) {
    await fetchUser()
  }
})

const route = useRoute()

const navigation = [
  { path: '/dashboard', label: 'Dashboard', icon: HomeIcon },
  { path: '/analyze', label: 'Analyze', icon: MagnifyingGlassIcon },
  { path: '/audit', label: 'AI Audit', icon: ShieldCheckIcon },
  { path: '/competitors', label: 'Competitors', icon: UsersIcon },
  { path: '/optimization', label: 'Optimization', icon: LightBulbIcon },
  { path: '/brand-voice', label: 'Brand Voice', icon: MicrophoneIcon },
  { path: '/settings', label: 'Settings', icon: Cog6ToothIcon },
]

const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}

const currentPageTitle = computed(() => {
  const item = navigation.find(n => isActive(n.path))
  return item?.label || 'Dashboard'
})

const userInitial = computed(() => {
  if (user.value?.full_name) return user.value.full_name[0].toUpperCase()
  if (user.value?.email) return user.value.email[0].toUpperCase()
  return 'U'
})
</script>
