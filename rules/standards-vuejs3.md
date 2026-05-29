---
paths:
  - "**/*.vue"
---

# Company Vue.js 3 Coding Standards

Vue.js 3 conventions combining official Vue.js best practices with company patterns.

**Based on**:
- Official Vue.js 3 Style Guide
- Vue.js 3 Composition API best practices
- Observed patterns in admin-ui codebase

---

## Component Structure

### Use Composition API with `<script setup>`
**Rule**: Always use Composition API with `<script setup lang="ts">`

```vue
<!-- ✅ Good - Composition API with script setup -->
<script lang="ts" setup>
import { ref, computed } from 'vue';

const count = ref(0);
const doubled = computed(() => count.value * 2);
</script>

<!-- ❌ Bad - Options API -->
<script lang="ts">
export default {
  data() {
    return { count: 0 };
  }
};
</script>
```

---

## File Naming

### PascalCase for Components
```
✅ Good:
- BaseCard.vue
- ConfirmDialog.vue
- GeneralCard.vue
- DataTableServerInfinite.vue

❌ Bad:
- baseCard.vue
- base-card.vue
- confirmDialog.vue
```

### Component Name Prefixes

**Base Components** (presentational, reusable):
```
BaseButton.vue
BaseCard.vue
BaseInput.vue
```

**Single-Instance Components** (The prefix):
```
TheHeader.vue
TheSidebar.vue
TheFooter.vue
```

**Feature Components**:
```
UserProfile.vue
OrderList.vue
PaymentForm.vue
```

---

## File Organization

### Group by Feature
```
src/
├── components/
│   ├── general/           # Reusable general components
│   │   ├── BaseCard.vue
│   │   ├── ConfirmDialog.vue
│   │   ├── forms/
│   │   ├── selectors/
│   │   ├── table/
│   │   └── navigation/
│   ├── partner/           # Partner-specific components
│   │   ├── GeneralCard.vue
│   │   └── APIKeyCard.vue
│   └── selector/          # Selector components
│       ├── Partner.vue
│       └── PaymentMethod.vue
├── pages/                 # Page components (routes)
│   └── solutionDelivery/
│       ├── partners/
│       │   ├── List.vue
│       │   └── Detail.vue
│       └── payouts/
│           ├── List.vue
│           └── Detail.vue
├── composables/           # Composition functions
├── stores/                # Pinia stores
└── types/                 # TypeScript types
```

---

## Component Definition

### Props with TypeScript
```vue
<script lang="ts" setup>
// ✅ Good - Typed props with interface
interface Props {
  title?: string;
  titleBackgroundColor?: string;
  titleTextColor?: string;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  titleBackgroundColor: '#00ACC1',
  titleTextColor: 'white',
  loading: false
});

// ❌ Bad - No types
const props = defineProps({
  title: String,
  loading: Boolean
});
</script>
```

### Required Props
```vue
<script lang="ts" setup>
// ✅ Good - Use required for mandatory props
interface Props {
  partnerId: string;        // Required (no ?)
  title?: string;           // Optional
}

const props = defineProps<Props>();
</script>
```

### Emits with TypeScript
```vue
<script lang="ts" setup>
// ✅ Good - Typed emits
const emit = defineEmits<{
  update: [value: string];
  delete: [id: number];
  confirm: [];
}>();

// Usage
emit('update', 'new value');
emit('delete', 123);
emit('confirm');

// ❌ Bad - No types
const emit = defineEmits(['update', 'delete']);
</script>
```

---

## Reactivity

### Use ref for Primitives and Objects
```typescript
// ✅ Good - ref for primitives
const count = ref(0);
const name = ref('');
const isLoading = ref(false);

// ✅ Good - ref for objects (easier to reassign)
const user = ref<User | null>(null);
user.value = newUser;

// ✅ Good - reactive for grouped state
const state = reactive({
  count: 0,
  name: '',
  isLoading: false
});
```

### Computed Properties
```typescript
// ✅ Good - Computed for derived state
const titleStyle = computed(() => {
  return {
    margin: '0px 0px 16px 0px',
    backgroundColor: props.titleBackgroundColor,
    color: props.titleTextColor
  };
});

// ❌ Bad - Function instead of computed
function titleStyle() {
  return {
    backgroundColor: props.titleBackgroundColor,
    color: props.titleTextColor
  };
}
```

---

## Template Best Practices

### v-if vs v-show
```vue
<template>
  <!-- ✅ Good - v-show for frequent toggles -->
  <div v-show="isVisible">Frequently toggled content</div>

  <!-- ✅ Good - v-if for conditional rendering -->
  <div v-if="user">{{ user.name }}</div>
  <div v-else>Loading...</div>
</template>
```

### Always Use :key with v-for
```vue
<template>
  <!-- ✅ Good - Unique key -->
  <div v-for="item in items" :key="item.id">
    {{ item.name }}
  </div>

  <!-- ❌ Bad - Missing key -->
  <div v-for="item in items">
    {{ item.name }}
  </div>

  <!-- ❌ Bad - Index as key -->
  <div v-for="(item, index) in items" :key="index">
    {{ item.name }}
  </div>
</template>
```

### Use Shorthand Syntax
```vue
<template>
  <!-- ✅ Good - Shorthand -->
  <button @click="handleClick" :disabled="loading">
    Submit
  </button>

  <!-- ❌ Bad - Full syntax -->
  <button v-on:click="handleClick" v-bind:disabled="loading">
    Submit
  </button>
</template>
```

### Component Naming in Templates
```vue
<template>
  <!-- ✅ Good - PascalCase (self-closing when no content) -->
  <BaseCard :title="title" :loading="loading">
    <FieldValue label="Name" :value="name" />
  </BaseCard>

  <!-- ❌ Bad - kebab-case -->
  <base-card :title="title">
    <field-value :label="label" />
  </base-card>
</template>
```

---

## Composables Pattern

### Composition Functions
```typescript
// composables/useUser.ts
import { ref, computed } from 'vue';

export function useUser(userId: string) {
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fullName = computed(() =>
    user.value
      ? `${user.value.firstName} ${user.value.lastName}`
      : ''
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

### Using Composables
```vue
<script lang="ts" setup>
import { useUser } from '@/composables/useUser';

const props = defineProps<{ userId: string }>();

const { user, loading, fullName, loadUser } = useUser(props.userId);

onMounted(() => {
  loadUser();
});
</script>
```

---

## Provide/Inject Pattern

### Provide at App Level
```vue
<!-- App.vue -->
<script lang="ts" setup>
import { ref, provide } from 'vue';

type ConfirmFn = (title: string, message: string) => Promise<boolean>;

const confirmDialog = ref<InstanceType<typeof ConfirmDialog> | null>(null);

const openConfirmDialog: ConfirmFn = (title, message) => {
  if (confirmDialog.value) {
    return confirmDialog.value.open(title, message);
  }
  return Promise.resolve(false);
};

provide('confirm', openConfirmDialog);
</script>
```

### Inject in Child Components
```vue
<script lang="ts" setup>
import { inject } from 'vue';

type ConfirmFn = (title: string, message: string) => Promise<boolean>;

const confirm = inject<ConfirmFn>('confirm');

async function deleteUser() {
  if (confirm) {
    const confirmed = await confirm('Delete User', 'Are you sure?');
    if (confirmed) {
      // Delete user
    }
  }
}
</script>
```

---

## Imports and Aliases

### Use @ Alias for src/
```vue
<script lang="ts" setup>
// ✅ Good - @ alias
import GeneralCard from '@/components/partner/GeneralCard.vue';
import APIKeyCard from '@/components/partner/APIKeyCard.vue';
import { useRoute } from 'vue-router';

// ❌ Bad - Relative paths
import GeneralCard from '../../../components/partner/GeneralCard.vue';
</script>
```

---

## Vuetify Integration

### Component Usage
```vue
<template>
  <!-- ✅ Good - Vuetify components -->
  <v-card
    class="mx-auto base-card"
    :loading="loading"
    variant="outlined"
  >
    <v-card-title class="custom-card-title">
      {{ title }}
    </v-card-title>
    <v-card-text>
      <slot />
    </v-card-text>
  </v-card>
</template>
```

### Layout with v-row and v-col
```vue
<template>
  <v-row>
    <v-col cols="12">
      <GeneralCard :partner-id="partnerId" :title="'General'" />
    </v-col>
  </v-row>
  <v-row>
    <v-col>
      <APIKeyCard :partner-id="partnerId" :title="'API Keys'" />
    </v-col>
  </v-row>
</template>
```

---

## Styling

### Scoped Styles
```vue
<style scoped>
/* ✅ Good - Scoped styles */
.custom-card-title {
  line-height: inherit;
  padding: 8px 16px;
  font-size: 1.0rem;
}

.base-card {
  border: thin solid rgba(0, 0, 0, 0.12);
}
</style>
```

### Global Styles in App.vue
```vue
<!-- App.vue -->
<style lang="css">
/* Global styles (no scoped) */
.v-form > .v-row > .v-col {
  padding-top: 0;
  padding-bottom: 0;
}

.v-table {
  font-size: 12px;
}
</style>
```

---

## Router Integration

### Access Route Params
```vue
<script lang="ts" setup>
import { useRoute } from 'vue-router';

const route = useRoute();

// ✅ Good - Type the route param
const partnerId = route.params.id as string;
</script>
```

---

## TypeScript Best Practices

### Type Component Refs
```vue
<script lang="ts" setup>
import ConfirmDialog from './components/general/ConfirmDialog.vue';

// ✅ Good - Type the ref
const confirmDialog = ref<InstanceType<typeof ConfirmDialog> | null>(null);
</script>
```

### Define Interfaces
```typescript
// ✅ Good - Define interfaces for data structures
interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
```

---

## Component Communication

### Props Down, Events Up
```vue
<!-- Parent.vue -->
<script lang="ts" setup>
const handleUpdate = (value: string) => {
  // Handle update
};
</script>

<template>
  <ChildComponent
    :value="myValue"
    @update="handleUpdate"
  />
</template>

<!-- Child.vue -->
<script lang="ts" setup>
interface Props {
  value: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{ update: [value: string] }>();

const updateValue = (newValue: string) => {
  emit('update', newValue);
};
</script>
```

---

## Performance Optimization

### Use v-once for Static Content
```vue
<template>
  <div v-once>
    <!-- Static content that never changes -->
    <h1>{{ staticTitle }}</h1>
  </div>
</template>
```

### Lazy Load Components
```typescript
// ✅ Good - Lazy load heavy components
const HeavyComponent = defineAsyncComponent(() =>
  import('./components/HeavyComponent.vue')
);
```

---

## Best Practices Summary

1. ✅ Always use Composition API with `<script setup lang="ts">`
2. ✅ Always type props and emits
3. ✅ Use PascalCase for component files
4. ✅ Use `ref` for reactive data
5. ✅ Use `computed` for derived state
6. ✅ Always provide `:key` for `v-for`
7. ✅ Use `@` alias for imports
8. ✅ Scope styles with `<style scoped>`
9. ✅ Use provide/inject for cross-cutting concerns
10. ✅ Extract reusable logic into composables

---

**Follow Vue.js 3 official style guide and these conventions for consistency.**
