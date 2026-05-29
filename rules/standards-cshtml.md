---
paths:
  - "**/*.cshtml"
  - "**/*.razor"
---

# CSHTML/Razor Standards

ASP.NET Core Razor Pages and MVC Views standards.

---

## Razor Syntax

### Use `@` for Code Blocks

```cshtml
@* ✅ Good - Inline expression *@
<h1>Welcome, @Model.UserName</h1>
<p>You have @Model.UnreadCount unread messages.</p>

@* ✅ Good - Code block *@
@{
    var greeting = $"Hello, {Model.UserName}";
    var isAdmin = User.IsInRole("Admin");
}

@* ✅ Good - Control structures *@
@if (Model.IsAuthenticated)
{
    <p>Welcome back!</p>
}
else
{
    <p>Please <a asp-page="/Login">log in</a>.</p>
}
```

---

## Security

### Always Encode Output

```cshtml
@* ✅ Good - Automatic HTML encoding *@
<p>@Model.UserInput</p>
<p>@Html.DisplayFor(m => m.UserInput)</p>

@* ❌ Bad - Raw HTML (XSS risk) *@
<p>@Html.Raw(Model.UserInput)</p>

@* ✅ Good - Use Raw only for trusted content *@
@Html.Raw(Model.SanitizedHtmlContent)
```

### CSRF Protection

```cshtml
@* ✅ Good - Anti-forgery token in forms *@
<form method="post">
    @Html.AntiForgeryToken()
    <input type="text" name="UserName" />
    <button type="submit">Submit</button>
</form>

@* ✅ Good - Tag helpers (automatic token) *@
<form asp-page="/Account/Edit" method="post">
    <input asp-for="UserName" />
    <button type="submit">Save</button>
</form>
```

---

## Tag Helpers

### Prefer Tag Helpers over HTML Helpers

```cshtml
@* ✅ Good - Tag helpers (clean syntax) *@
<form asp-page="/Users/Edit" asp-route-id="@Model.UserId" method="post">
    <label asp-for="Email"></label>
    <input asp-for="Email" class="form-control" />
    <span asp-validation-for="Email" class="text-danger"></span>
    <button type="submit">Save</button>
</form>

@* ❌ Bad - HTML helpers (verbose) *@
@using (Html.BeginForm("Edit", "Users", new { id = Model.UserId }, FormMethod.Post))
{
    @Html.LabelFor(m => m.Email)
    @Html.TextBoxFor(m => m.Email, new { @class = "form-control" })
    @Html.ValidationMessageFor(m => m.Email, null, new { @class = "text-danger" })
    <button type="submit">Save</button>
}
```

### Common Tag Helpers

```cshtml
@* Links *@
<a asp-page="/Users/Details" asp-route-id="@user.Id">View</a>
<a asp-controller="Home" asp-action="Index">Home</a>

@* Images *@
<img asp-append-version="true" src="~/images/logo.png" alt="Logo" />

@* Environment-specific content *@
<environment include="Development">
    <link rel="stylesheet" href="~/css/site.css" />
</environment>
<environment exclude="Development">
    <link rel="stylesheet" href="~/css/site.min.css" asp-append-version="true" />
</environment>

@* Cache *@
<cache expires-after="@TimeSpan.FromMinutes(10)">
    @await Component.InvokeAsync("RecentPosts")
</cache>
```

---

## Partial Views

### Use Partial for Reusable UI

```cshtml
@* ✅ Good - Partial tag helper *@
<partial name="_UserCard" model="@Model.User" />
<partial name="Shared/_Pagination" model="@Model.PageInfo" />

@* ✅ Good - Partial with view data *@
<partial name="_StatusBadge"
         model="@Model.Status"
         view-data='new ViewDataDictionary(ViewData) { { "Size", "large" } }' />

@* ❌ Bad - HTML helper (verbose) *@
@Html.Partial("_UserCard", Model.User)
```

### Naming Convention

```
Views/
├── Shared/
│   ├── _Layout.cshtml          # Layout (starts with _)
│   ├── _UserCard.cshtml        # Partial (starts with _)
│   └── _ValidationScriptsPartial.cshtml
├── Users/
│   ├── Index.cshtml            # Page (no underscore)
│   ├── Details.cshtml
│   └── _UserForm.cshtml        # Partial (starts with _)
```

---

## View Components

### Use for Complex Reusable Logic

```csharp
// ViewComponents/RecentPostsViewComponent.cs
public class RecentPostsViewComponent : ViewComponent
{
    private readonly IPostService _postService;

    public RecentPostsViewComponent(IPostService postService)
    {
        _postService = postService;
    }

    public async Task<IViewComponentResult> InvokeAsync(int count = 5)
    {
        var posts = await _postService.GetRecentPostsAsync(count);
        return View(posts);
    }
}
```

```cshtml
@* Views/Shared/Components/RecentPosts/Default.cshtml *@
<div class="recent-posts">
    <h3>Recent Posts</h3>
    <ul>
        @foreach (var post in Model)
        {
            <li>
                <a asp-page="/Posts/Details" asp-route-id="@post.Id">
                    @post.Title
                </a>
                <span class="date">@post.PublishedDate.ToString("MMM dd, yyyy")</span>
            </li>
        }
    </ul>
</div>
```

```cshtml
@* Usage in page *@
@await Component.InvokeAsync("RecentPosts", new { count = 10 })
<vc:recent-posts count="10"></vc:recent-posts>
```

---

## Layouts

### Define Common Layout

```cshtml
@* Views/Shared/_Layout.cshtml *@
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>@ViewData["Title"] - My App</title>
    <link rel="stylesheet" href="~/css/site.min.css" asp-append-version="true" />
    @await RenderSectionAsync("Styles", required: false)
</head>
<body>
    <header>
        <nav>@await Component.InvokeAsync("Navigation")</nav>
    </header>
    <main>
        @RenderBody()
    </main>
    <footer>
        <p>&copy; @DateTime.Now.Year - My Company</p>
    </footer>
    <script src="~/js/site.min.js" asp-append-version="true"></script>
    @await RenderSectionAsync("Scripts", required: false)
</body>
</html>
```

```cshtml
@* Pages/Index.cshtml *@
@page
@model IndexModel
@{
    ViewData["Title"] = "Home";
}

@section Styles {
    <link rel="stylesheet" href="~/css/home.css" />
}

<h1>@ViewData["Title"]</h1>
<p>Welcome to the home page.</p>

@section Scripts {
    <script src="~/js/home.js"></script>
}
```

---

## Data Binding

### Strongly-Typed Models

```cshtml
@* ✅ Good - Strongly typed *@
@model MyApp.Models.UserViewModel

<h1>@Model.FullName</h1>
<p>Email: @Model.Email</p>
<p>Joined: @Model.JoinDate.ToString("yyyy-MM-dd")</p>

@* ❌ Bad - ViewBag/ViewData (weak typing) *@
<h1>@ViewBag.FullName</h1>
<p>Email: @ViewData["Email"]</p>
```

### Form Binding

```cshtml
@model MyApp.Models.EditUserModel

<form asp-page="/Users/Edit" method="post">
    <div class="form-group">
        <label asp-for="FirstName"></label>
        <input asp-for="FirstName" class="form-control" />
        <span asp-validation-for="FirstName" class="text-danger"></span>
    </div>

    <div class="form-group">
        <label asp-for="Email"></label>
        <input asp-for="Email" type="email" class="form-control" />
        <span asp-validation-for="Email" class="text-danger"></span>
    </div>

    <div class="form-group">
        <label asp-for="Role"></label>
        <select asp-for="Role" asp-items="Model.RoleOptions" class="form-control">
            <option value="">-- Select Role --</option>
        </select>
        <span asp-validation-for="Role" class="text-danger"></span>
    </div>

    <button type="submit" class="btn btn-primary">Save</button>
</form>

@section Scripts {
    <partial name="_ValidationScriptsPartial" />
}
```

---

## Client-Side Validation

### Enable Unobtrusive Validation

```cshtml
@* ✅ Always include validation scripts *@
@section Scripts {
    <partial name="_ValidationScriptsPartial" />
}

@* _ValidationScriptsPartial.cshtml *@
<script src="~/lib/jquery-validation/dist/jquery.validate.min.js"></script>
<script src="~/lib/jquery-validation-unobtrusive/jquery.validate.unobtrusive.min.js"></script>
```

---

## Conditional Rendering

### Use `@if`, `@foreach`, `@switch`

```cshtml
@* ✅ Good - Clean conditional rendering *@
@if (Model.Users.Any())
{
    <table class="table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            @foreach (var user in Model.Users)
            {
                <tr>
                    <td>@user.FullName</td>
                    <td>@user.Email</td>
                    <td>
                        <a asp-page="/Users/Edit" asp-route-id="@user.Id">Edit</a>
                        @if (User.IsInRole("Admin"))
                        {
                            <a asp-page="/Users/Delete" asp-route-id="@user.Id">Delete</a>
                        }
                    </td>
                </tr>
            }
        </tbody>
    </table>
}
else
{
    <p class="text-muted">No users found.</p>
}
```

---

## Best Practices

### Keep Views Simple

```cshtml
@* ✅ Good - Logic in PageModel/ViewModel *@
@model UserListModel

<h1>Users (@Model.UserCount)</h1>
@foreach (var user in Model.ActiveUsers)
{
    <div class="user-card">@user.DisplayName</div>
}

@* ❌ Bad - Complex logic in view *@
@{
    var activeUsers = Model.Users
        .Where(u => u.IsActive && !u.IsDeleted)
        .OrderBy(u => u.LastName)
        .ToList();
    var count = activeUsers.Count;
}
<h1>Users (@count)</h1>
```

### Use Display Templates

```cshtml
@* EditorTemplates/DateTime.cshtml *@
@model DateTime?
<input type="datetime-local"
       name="@ViewData.ModelMetadata.PropertyName"
       value="@(Model?.ToString("yyyy-MM-ddTHH:mm"))"
       class="form-control" />

@* Usage *@
@Html.EditorFor(m => m.BirthDate)
```

### Comments

```cshtml
@* ✅ Good - Razor comments (not sent to client) *@
@* TODO: Add pagination controls *@
@* This section displays user statistics *@

@* ❌ Bad - HTML comments (visible in page source) *@
<!-- TODO: Add pagination -->
<!-- Contains sensitive development notes -->
```

---

**These standards ensure secure, maintainable Razor views.**
