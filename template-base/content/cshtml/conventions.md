## ASP.NET MVC / Razor Pages Conventions

### Project Structure

```
MyApp/
├── Controllers/       # MVC controllers
├── Models/            # ViewModels and domain models
│   ├── ViewModels/    # View-specific models
│   └── DTOs/          # Data transfer objects
├── Views/             # Razor views (.cshtml)
│   ├── Shared/        # Layouts, partials
│   └── [Controller]/  # Views per controller
├── Pages/             # Razor Pages (if mixed)
├── Services/          # Business logic
├── Repositories/      # Data access
└── wwwroot/           # Static files (css, js, images)
```

### Controllers

```csharp
// ✅ Good - Thin controllers, delegate to services
[Route("[controller]")]
public class UsersController : Controller
{
    private readonly IUserService _service;

    public UsersController(IUserService service) => _service = service;

    [HttpGet("{id:int}")]
    public async Task<IActionResult> Details(int id)
    {
        var vm = await _service.GetUserDetailsAsync(id);
        if (vm is null) return NotFound();
        return View(vm);
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Create(CreateUserViewModel vm)
    {
        if (!ModelState.IsValid) return View(vm);
        await _service.CreateAsync(vm);
        return RedirectToAction(nameof(Index));
    }
}
```

### ViewModels

```csharp
// ✅ Good - ViewModel per view, data annotations for validation
public class CreateUserViewModel
{
    [Required]
    [StringLength(100, MinimumLength = 2)]
    public string Name { get; set; } = string.Empty;

    [Required]
    [EmailAddress]
    public string Email { get; set; } = string.Empty;
}
```

### Razor Views

```html
@* ✅ Good - Tag helpers over HTML helpers *@
<form asp-action="Create" asp-controller="Users" method="post">
    <div asp-validation-summary="ModelOnly"></div>

    <label asp-for="Name"></label>
    <input asp-for="Name" class="form-control" />
    <span asp-validation-for="Name"></span>

    <button type="submit">Create</button>
</form>

@* ✅ Good - Typed views *@
@model CreateUserViewModel
```

### Layouts & Partial Views

```html
@* _Layout.cshtml: shared structure *@
@* Partial views: reusable UI fragments *@
@await Html.PartialAsync("_UserCard", user)

@* View Components: for complex reusable UI with logic *@
@await Component.InvokeAsync("RecentOrders", new { userId = Model.Id })
```

### Routing

```csharp
// ✅ Good - Attribute routing, explicit routes
[Route("api/[controller]")]
[Route("[controller]/[action]")]

// ✅ Good - Route constraints
[HttpGet("{id:int:min(1)}")]
[HttpGet("{slug:alpha}")]
```

### C# Conventions

Same as .NET conventions — see naming, async/await, null safety, LINQ, and DI patterns above.

---
