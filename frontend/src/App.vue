<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './stores/user'

onMounted(() => {
  const userStore = useUserStore()
  // Zombie Check: Token exists but User object is missing (due to localStorage update lag)
  if (userStore.token && !userStore.user) {
    console.warn('Zombie session detected: Token exists without User profile. Force logout.')
    userStore.logout()
  }
})
</script>

<style>
/* Global styles if needed */
body {
  margin: 0;
  font-family: 'Lato', sans-serif;
}
</style>
