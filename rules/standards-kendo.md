---
paths:
  - "**/*.ts"
  - "**/*.js"
  - "**/*.cshtml"
---

# Kendo UI Standards

Kendo UI widget standards with TypeScript/JavaScript integration.

---

## Widget Initialization

### TypeScript

```typescript
// ✅ Good - Type-safe initialization
interface GridOptions extends kendo.ui.GridOptions {
    dataSource: kendo.data.DataSourceOptions;
    columns: kendo.ui.GridColumn[];
}

const gridOptions: GridOptions = {
    dataSource: {
        transport: {
            read: {
                url: "/api/users",
                dataType: "json"
            }
        },
        schema: {
            model: {
                id: "id",
                fields: {
                    id: { type: "number" },
                    name: { type: "string" },
                    email: { type: "string" }
                }
            }
        },
        pageSize: 20
    },
    columns: [
        { field: "id", title: "ID", width: 80 },
        { field: "name", title: "Name" },
        { field: "email", title: "Email" },
        { command: ["edit", "destroy"], width: 200 }
    ],
    pageable: true,
    sortable: true,
    filterable: true,
    editable: "inline"
};

$("#grid").kendoGrid(gridOptions);
```

---

## Data Source Configuration

```typescript
// ✅ Good - Separate DataSource for reusability
const userDataSource = new kendo.data.DataSource({
    transport: {
        read: { url: "/api/users", type: "GET" },
        create: { url: "/api/users", type: "POST" },
        update: { url: "/api/users/{0}", type: "PUT" },
        destroy: { url: "/api/users/{0}", type: "DELETE" }
    },
    schema: {
        model: {
            id: "id",
            fields: {
                id: { type: "number", editable: false },
                name: { type: "string", validation: { required: true } },
                email: { type: "string", validation: { required: true, email: true } },
                isActive: { type: "boolean", defaultValue: true }
            }
        }
    },
    pageSize: 20,
    serverPaging: true,
    serverFiltering: true,
    serverSorting: true
});

// Use in multiple widgets
$("#grid").kendoGrid({ dataSource: userDataSource });
$("#chart").kendoChart({ dataSource: userDataSource });
```

---

## Grid Configuration

```typescript
// ✅ Good - Comprehensive grid setup
$("#usersGrid").kendoGrid({
    dataSource: userDataSource,
    columns: [
        {
            field: "id",
            title: "ID",
            width: 80,
            filterable: false
        },
        {
            field: "name",
            title: "Name",
            template: (dataItem: any) => `<strong>${kendo.htmlEncode(dataItem.name)}</strong>`
        },
        {
            field: "email",
            title: "Email",
            editor: (container: JQuery, options: any) => {
                $('<input data-bind="value:' + options.field + '"/>')
                    .appendTo(container)
                    .kendoMaskedTextBox({ mask: "email" });
            }
        },
        {
            field: "isActive",
            title: "Active",
            width: 100,
            template: (dataItem: any) =>
                `<input type="checkbox" ${dataItem.isActive ? "checked" : ""} disabled />`
        },
        {
            command: [
                { name: "edit", text: "Edit" },
                { name: "destroy", text: "Delete" }
            ],
            width: 200
        }
    ],
    toolbar: ["create", "excel"],
    excel: {
        fileName: "Users.xlsx",
        allPages: true
    },
    pageable: {
        refresh: true,
        pageSizes: [10, 20, 50, 100],
        buttonCount: 5
    },
    sortable: {
        mode: "multiple",
        allowUnsort: true
    },
    filterable: {
        mode: "row"
    },
    editable: {
        mode: "inline",
        confirmation: "Are you sure you want to delete this user?"
    },
    height: 550
});
```

---

## Event Handling

```typescript
// ✅ Good - Type-safe event handlers
$("#grid").kendoGrid({
    dataSource: userDataSource,
    columns: [/* ... */],
    change: function(e: kendo.ui.GridChangeEvent) {
        const selectedRow = this.select();
        const dataItem = this.dataItem(selectedRow);
        console.log("Selected user:", dataItem);
    },
    save: function(e: kendo.ui.GridSaveEvent) {
        console.log("Saving user:", e.model);
    },
    remove: function(e: kendo.ui.GridRemoveEvent) {
        console.log("Removing user:", e.model);
    },
    edit: function(e: kendo.ui.GridEditEvent) {
        if (!e.model.isNew()) {
            e.container.find("input[name='email']").attr("readonly", true);
        }
    }
});

// ✅ Good - External event binding
const grid = $("#grid").data("kendoGrid");
grid.bind("dataBound", (e: kendo.ui.GridDataBoundEvent) => {
    console.log("Grid data bound");
});
```

---

## CRUD Operations

```typescript
// ✅ Good - Programmatic CRUD
const grid = $("#grid").data("kendoGrid");

// Create
const newUser = { name: "John Doe", email: "john@example.com" };
grid.dataSource.add(newUser);
grid.dataSource.sync();

// Read
grid.dataSource.read();

// Update
const dataItem = grid.dataItem(grid.tbody.find("tr:first"));
dataItem.set("name", "Jane Doe");
grid.dataSource.sync();

// Delete
grid.removeRow(grid.tbody.find("tr:first"));
```

---

## Window/Dialog

```typescript
// ✅ Good - Modal window
const window = $("#window").kendoWindow({
    title: "User Details",
    modal: true,
    width: 600,
    height: 400,
    visible: false,
    actions: ["Close"],
    close: function() {
        this.center();
    }
}).data("kendoWindow");

// Show with content
window.content("<p>Loading...</p>");
window.center().open();

// Load remote content
window.refresh({
    url: "/api/users/123",
    type: "GET"
});
```

---

## Validator

```typescript
// ✅ Good - Form validation
const validator = $("#userForm").kendoValidator({
    rules: {
        email: function(input: JQuery) {
            if (input.is("[name=email]")) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                return emailRegex.test(input.val() as string);
            }
            return true;
        },
        minAge: function(input: JQuery) {
            if (input.is("[name=age]")) {
                return parseInt(input.val() as string) >= 18;
            }
            return true;
        }
    },
    messages: {
        email: "Please enter a valid email address",
        minAge: "Must be at least 18 years old"
    }
}).data("kendoValidator");

// Validate
if (validator.validate()) {
    // Submit form
}
```

---

## Best Practices

### Destroy Widgets

```typescript
// ✅ Good - Clean up on page unload
$(window).on("beforeunload", () => {
    const grid = $("#grid").data("kendoGrid");
    if (grid) {
        grid.destroy();
    }
});
```

### Template Encoding

```typescript
// ✅ Good - Encode user input
columns: [{
    template: (dataItem: any) => kendo.htmlEncode(dataItem.userInput)
}]

// ❌ Bad - XSS vulnerability
columns: [{
    template: (dataItem: any) => dataItem.userInput
}]
```

### Performance

```typescript
// ✅ Good - Virtual scrolling for large datasets
$("#grid").kendoGrid({
    scrollable: {
        virtual: true
    },
    height: 550,
    dataSource: {
        serverPaging: true,
        pageSize: 50
    }
});
```

---

**Build interactive UIs with Kendo consistently.**
