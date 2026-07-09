## Vue.js 3 Conventions

### Component Structure (Composition API)

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';

// Props
interface Props {
  userId: string;
  showAvatar?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showAvatar: true
});

// Emits
const emit = defineEmits<{
  userLoaded: [user: User];
  error: [error: Error];
}>();

// State
const user = ref<User | null>(null);
const loading = ref(false);

// Computed
const fullName = computed(() =>
  user.value ? `${user.value.firstName} ${user.value.lastName}` : ''
);

// Methods
async function loadUser() {
  loading.value = true;
  try {
    user.value = await userService.getById(props.userId);
    emit('userLoaded', user.value);
  } catch (error) {
    emit('error', error as Error);
  } finally {
    loading.value = false;
  }
}

// Lifecycle
onMounted(() => {
  loadUser();
});
</script>

<template>
  <div class="user-profile">
    <div v-if="loading">Loading...</div>
    <div v-else-if="user">
      <h1>{{ fullName }}</h1>
      <img v-if="showAvatar" :src="user.avatar" :alt="fullName" />
    </div>
  </div>
</template>

<style scoped>
.user-profile {
  padding: 1rem;
}
</style>
```

### Composables

```typescript
// composables/useUser.ts
import { ref, computed } from 'vue';
import type { User } from '@/types';

export function useUser(userId: string) {
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fullName = computed(() =>
    user.value ? `${user.value.firstName} ${user.value.lastName}` : ''
  );

  async function loadUser() {
    loading.value = true;
    error.value = null;
    try {
      user.value = await userService.getById(userId);
    } catch (err) {
      error.value = err as Error;
    } finally {
      loading.value = false;
    }
  }

  return {
    user,
    loading,
    error,
    fullName,
    loadUser
  };
}
```

### Pinia Store

```typescript
// stores/user.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { User } from '@/types';

export const useUserStore = defineStore('user', () => {
  // State
  const currentUser = ref<User | null>(null);
  const isAuthenticated = ref(false);

  // Getters
  const fullName = computed(() =>
    currentUser.value
      ? `${currentUser.value.firstName} ${currentUser.value.lastName}`
      : ''
  );

  // Actions
  async function login(email: string, password: string) {
    const user = await authService.login(email, password);
    currentUser.value = user;
    isAuthenticated.value = true;
  }

  function logout() {
    currentUser.value = null;
    isAuthenticated.value = false;
  }

  return {
    currentUser,
    isAuthenticated,
    fullName,
    login,
    logout
  };
});
```

---
