## Kotlin/Android Coding Conventions

### Naming Conventions

**Files:**
- One class per file
- File name matches class name: `UserRepository.kt`
- Compose screens: `FeatureScreen.kt`
- ViewModels: `FeatureViewModel.kt`

**Classes & Functions:**
- PascalCase for classes: `UserRepository`, `LoginViewModel`
- camelCase for functions: `getUserById()`, `processPayment()`
- SCREAMING_SNAKE_CASE for constants: `MAX_RETRY_COUNT`, `API_TIMEOUT`

**Variables:**
- camelCase: `userName`, `isLoading`
- Prefix backing properties with underscore: `_uiState` (private), `uiState` (public)

### Package Structure

```
app.yourapp/
├── ui/              # UI Layer (Activities, Composables, ViewModels)
├── domain/          # Domain Layer (Use Cases, Models, Repository interfaces)
├── data/            # Data Layer (Repository implementations, Data sources)
└── di/              # Dependency Injection (Hilt modules)
```

### Architecture Patterns

**Clean Architecture Layers:**
- **UI Layer**: Compose + ViewModel (no business logic)
- **Domain Layer**: Pure Kotlin (no Android dependencies)
- **Data Layer**: Repository pattern, data sources

**Dependency Rule:**
UI → Domain ← Data (dependencies point inward)

### Kotlin Best Practices

**Null Safety:**
```kotlin
// ✅ Good - Use safe calls
val length = user?.name?.length ?: 0

// ❌ Bad - Avoid !! operator
val length = user!!.name!!.length
```

**Immutability:**
```kotlin
// ✅ Good - Prefer val (immutable)
val user = User(id = 1, name = "John")

// ❌ Bad - Avoid var when possible
var user = User(id = 1, name = "John")
```

**Data Classes:**
```kotlin
// ✅ Good - Use data classes for models
data class User(val id: Int, val name: String)

// ❌ Bad - Don't write boilerplate
class User(val id: Int, val name: String) {
    override fun equals(other: Any?): Boolean { ... }
    override fun hashCode(): Int { ... }
}
```

**Sealed Classes for State:**
```kotlin
// ✅ Good - Exhaustive when expressions
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String) : Result<Nothing>()
    data object Loading : Result<Nothing>()
}
```

### Coroutines & Flow

**Structured Concurrency:**
```kotlin
// ✅ Good - Use viewModelScope
viewModelScope.launch {
    userRepository.getUser()
        .collect { user -> _uiState.value = user }
}

// ❌ Bad - Don't use GlobalScope
GlobalScope.launch { /* ... */ }
```

**Flow Operators:**
```kotlin
// ✅ Good - Transform data with operators
repository.getUsers()
    .map { it.filter { user -> user.isActive } }
    .catch { emit(emptyList()) }
    .collect { _users.value = it }
```

### Compose Best Practices

**Stateless Composables:**
```kotlin
// ✅ Good - State hoisting
@Composable
fun Counter(count: Int, onIncrement: () -> Unit) {
    Button(onClick = onIncrement) {
        Text("Count: $count")
    }
}

// ❌ Bad - Internal state in reusable composable
@Composable
fun Counter() {
    var count by remember { mutableStateOf(0) }
    Button(onClick = { count++ }) { Text("$count") }
}
```

**Remember & State:**
```kotlin
// ✅ Good - Use remember for expensive calculations
val sortedList = remember(items) { items.sortedBy { it.name } }

// ✅ Good - collectAsState for Flow
val uiState by viewModel.uiState.collectAsState()
```

### Testing Patterns

**Unit Tests:**
```kotlin
// ✅ Good - Test use cases and ViewModels
class GetUserUseCaseTest {
    private val repository: UserRepository = mockk()
    private val useCase = GetUserUseCase(repository)
    
    @Test
    fun `should return user when repository succeeds`() = runTest {
        coEvery { repository.getUser(1) } returns flowOf(testUser)
        
        val result = useCase(1).first()
        
        assertEquals(testUser, result)
    }
}
```

**Compose Tests:**
```kotlin
// ✅ Good - Test UI behavior
@Test
fun `should display user name when loaded`() {
    composeTestRule.setContent {
        UserScreen(user = testUser)
    }
    
    composeTestRule
        .onNodeWithText("John Doe")
        .assertIsDisplayed()
}
```

### Code Quality

**Lint Rules:**
- Enable all Android lint checks
- Treat warnings as errors in CI
- Use ktlint or detekt for Kotlin style

**Coverage Target:**
- Unit tests: ≥ 80% coverage
- Focus on domain and ViewModel layers
- UI tests for critical user flows

### Android Specifics

**Permissions:**
- Request at runtime (Android 6+)
- Explain why permission is needed
- Handle denial gracefully

**Lifecycle:**
- Respect Activity/Fragment lifecycle
- Use `viewModelScope` for coroutines
- Cancel work in `onDestroy` if needed

**Resources:**
- No hardcoded strings (use `strings.xml`)
- No hardcoded colors (use `colors.xml` or theme)
- Use vector drawables over PNGs
