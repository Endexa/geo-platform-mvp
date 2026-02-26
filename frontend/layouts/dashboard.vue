<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Mobile overlay backdrop -->
    <div
      v-if="!isDesktop && sidebarOpen"
      class="fixed inset-0 bg-black/50 z-20 transition-opacity duration-200"
      @click="sidebarOpen = false"
    />

    <!-- Sidebar -->
    <aside
      class="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 flex flex-col z-30 transition-transform duration-200"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <!-- Logo -->
      <div class="p-6 border-b border-gray-200">
        <h1 class="text-2xl font-bold text-primary-600">GEO Platform</h1>
        <p class="text-sm text-gray-500">Optimization Suite</p>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
        <NuxtLink
          v-for="item in navigation"
          :key="item.path"
          :to="item.path"
          class="flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors duration-200 cursor-pointer"
          :class="isActive(item.path) ? 'bg-primary-50 text-primary-700' : 'text-gray-700 hover:bg-gray-100'"
          @click="closeSidebarOnMobile"
        >
          <component :is="item.icon" class="w-5 h-5 mr-3 shrink-0" />
          {{ item.label }}
        </NuxtLink>
      </nav>

      <!-- Upgrade CTA (hidden for pro users) -->
      <div v-if="!isProUser" class="p-4 m-4 bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg text-white">
        <h3 class="font-semibold mb-1">Upgrade to Pro</h3>
        <p class="text-xs text-primary-100 mb-3">Unlock advanced features</p>
        <NuxtLink
          to="/pricing"
          class="block w-full px-3 py-2 bg-white text-primary-600 rounded-md text-sm font-medium text-center hover:bg-primary-50 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-600"
        >
          Upgrade Now
        </NuxtLink>
      </div>
    </aside>

    <!-- Main Content -->
    <div
      class="transition-all duration-200"
      :class="sidebarOpen && isDesktop ? 'lg:ml-64' : 'ml-0'"
    >
      <!-- Top Bar -->
      <header class="bg-white border-b border-gray-200 px-4 py-4 lg:px-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <!-- Hamburger toggle (visible on non-desktop) -->
            <button
              class="lg:hidden p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors duration-200 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500"
              @click="sidebarOpen = !sidebarOpen"
              aria-label="Toggle sidebar"
            >
              <Bars3Icon class="w-5 h-5" />
            </button>

            <!-- Breadcrumbs -->
            <div class="flex items-center space-x-2 text-sm">
              <span class="text-gray-500 hidden sm:inline">Dashboard</span>
              <span class="text-gray-400 hidden sm:inline">/</span>
              <span class="text-gray-900 font-medium">{{ currentPageTitle }}</span>
            </div>
          </div>

          <!-- User Menu -->
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600 hidden sm:inline">{{ user?.email }}</span>
            <button
              @click="logout"
              class="text-sm text-gray-500 hover:text-gray-700 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 rounded px-2 py-1 transition-colors duration-200"
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
      <main class="p-4 lg:p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import {
  HomeIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  UsersIcon,
  BuildingOfficeIcon,
  LightBulbIcon,
  MicrophoneIcon,
  Cog6ToothIcon,
  Bars3Icon,
} from '@heroicons/vue/24/outline'

const { isLoggedIn, user, logout, fetchUser } = useAuth()
const { isProUser } = useSubscription()

// Responsive sidebar
const isDesktop = useMediaQuery('(min-width: 1024px)')
const sidebarOpen = ref(true)

// Auto-collapse sidebar when transitioning from desktop to tablet/mobile
watch(isDesktop, (desktop) => {
  sidebarOpen.value = desktop
})

// Close sidebar when navigating on mobile/tablet
function closeSidebarOnMobile() {
  if (!isDesktop.value) {
    sidebarOpen.value = false
  }
}

// Fetch user info on mount if we have token but no user
onMounted(async () => {
  if (!isLoggedIn.value) {
    await navigateTo('/login', { replace: true })
    return
  }
  if (!user.value) {
    await fetchUser()
  }
  // Initialize sidebar state based on current viewport
  sidebarOpen.value = isDesktop.value
})

const route = useRoute()

const navigation = [
  { path: '/dashboard', label: 'Dashboard', icon: HomeIcon },
  { path: '/analyze', label: 'Analyze', icon: MagnifyingGlassIcon },
  { path: '/audit', label: 'AI Audit', icon: ShieldCheckIcon },
  { path: '/competitors', label: 'Competitors', icon: UsersIcon },
  { path: '/brands', label: 'Brands', icon: BuildingOfficeIcon },
  { path: '/recommendations', label: 'Recommendations', icon: LightBulbIcon },
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
