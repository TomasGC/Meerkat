---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

# Company TypeScript Coding Standards

TypeScript conventions based on existing company codebase.

**Source**: Observed patterns in Lmk.Limoney.BackOffice TypeScript code

---

## File Naming

### PascalCase for Files
```
✅ Good:
- AlertManager.ts
- FormManager.ts
- UserService.ts
- IComponent.ts

❌ Bad:
- alertManager.ts
- alert-manager.ts
- alert_manager.ts
```

### Organize by Feature
```
scripts/
├── AlertManager.ts
├── FormManager.ts
├── pages/
│   ├── AccountDetails.ts
│   ├── UsersList.ts
│   └── OrderDetails.ts
├── components/
│   ├── IComponent.ts
│   └── MermaidDiagramComponent.ts
└── behaviors/
    ├── AutoSelectFirstBehavior.ts
    └── ViewDetailsBehavior.ts
```

---

## Naming Conventions

### Parameters: Prefixed with `p` (LEGACY - Being Phased Out)

**⚠️ Legacy Convention**: Existing codebase uses lowercase `p` prefix for parameters. This is **legacy** and being phased out. Do NOT use in new code.

**Migration Status**:
- ❌ **Legacy code** (being migrated) - Uses `p` prefix
- ✅ **New code** (use this) - Standard TypeScript naming (no prefix)

```typescript
// ❌ LEGACY - Parameter p prefix (DO NOT USE in new code)
function handleUrlAlerts(pMessage: string, pDelay: number | false) {
    let notification = getNotification(pMessage, pDelay);
    notification.show();
}

function getNotification(pAlert: Alert, pIsSanitationAlreadyDone: boolean = false): Noty {
    if (pIsSanitationAlreadyDone) {
        return createNotification(pAlert);
    }
    // ...
}

// ✅ MODERN - Standard TypeScript naming (USE THIS in new code)
function handleUrlAlerts(message: string, delay: number | false) {
    const notification = getNotification(message, delay);
    notification.show();
}

function getNotification(alert: Alert, isSanitationAlreadyDone: boolean = false): Noty {
    if (isSanitationAlreadyDone) {
        return createNotification(alert);
    }
    // ...
}
```

**Why phasing out**:
- Non-standard (not used in TypeScript ecosystem)
- Reduces readability (extra character for no benefit)
- Conflicts with modern IDE features (parameter hints)

**Migration approach**:
- New files: Use standard naming (no `p`)
- Existing files: Gradually remove `p` when refactoring
- No mass rename (avoid merge conflicts)

### Interfaces: PascalCase
```typescript
// ✅ Good
interface AlertConfig {
    type: AlertType;
    parameterName: string;
    className: "success" | "danger" | "warning";
    delay: number | false;
}

interface Alert {
    config: AlertConfig;
    content: string;
}
```

### Enums: PascalCase
```typescript
// ✅ Good
enum AlertType {
    Success,
    Warning,
    Error
}
```

### Variables and Functions: camelCase
```typescript
// ✅ Good - Variables
let properText: string;
let urlParameters: { [type: number]: AlertConfig } = { };
const submitFormElementSelector = "#submit.btn-action[formaction]";

// ✅ Good - Functions
function handleUrlAlerts() { }
function searchFirstAlert(): Alert { }
function sanitizeMessage(message: string): string { }

// ✅ Good - Exported functions
export function getErrorNotification(pMessage?: string, pDelay: number | false = false): Noty { }
export function showMessage(pMessage: string, pDelay: number = 3000): Noty { }
```

### jQuery Variables: Prefixed with `_`
```typescript
// ✅ Good - jQuery objects prefixed with underscore
$(".validation-summary-errors li").each(function () {
    let _this = $(this);
    let validatedElements = $("[data-val=true]").filter((i, e) =>
        elementHasErrorMessage(e, _this.html())
    );
});
```

---

## Type Annotations

### Always Type Parameters and Return Values
```typescript
// ✅ Good - Explicit types
function getNotification(pAlert: Alert, pIsSanitationAlreadyDone: boolean = false): Noty {
    // Implementation
}

function sanitizeMessage(pMessage: string): string {
    return pMessage.replace(/</g, "").replace(/>/g, "").replace("\"", "");
}

// ❌ Bad - Missing types
function getNotification(pAlert, pIsSanitationAlreadyDone) {
    // Implementation
}
```

### Use Union Types
```typescript
// ✅ Good - Union types
interface AlertConfig {
    type: AlertType;
    className: "success" | "danger" | "warning";
    delay: number | false;  // Can be number or false
}
```

### Index Signatures
```typescript
// ✅ Good - Typed object with index signature
const urlParameters: { [type: number]: AlertConfig } = {
    [AlertType.Success]: { /* config */ },
    [AlertType.Warning]: { /* config */ },
    [AlertType.Error]: { /* config */ }
};
```

---

## Import Organization

### Reference Paths for Type Definitions
```typescript
///<reference path="../../wwwroot/lib/noty/index.d.ts"/>
///<reference path="../typings/jquery.validation.d.ts"/>
```

### Group Imports
```typescript
// External libraries
import * as UrlManager from "./UrlManager";
import * as Noty from "noty";
import ConfirmAction from "ConfirmAction";

// Internal modules
import * as ErrorManager from "ErrorManager";
```

---

## Class Structure

### Properties Before Methods
```typescript
class MyManager {
    // Constants
    private readonly MAX_RETRIES = 3;

    // Private fields
    private _config: Config;
    private _isInitialized: boolean;

    // Constructor
    constructor(pConfig: Config) {
        this._config = pConfig;
        this._isInitialized = false;
    }

    // Public methods
    public init(): void {
        this._isInitialized = true;
    }

    // Private methods
    private validate(): boolean {
        return this._isInitialized;
    }
}
```

---

## Function Patterns

### Exported Module Functions
```typescript
// ✅ Good - Specific exported functions
export function getErrorNotification(pMessage?: string, pDelay: number | false = false): Noty {
    let alert = makeAlert(AlertType.Error, pMessage, pDelay);
    return getNotification(alert);
}

export function showMessage(pMessage: string, pDelay: number = 3000): Noty {
    let notification = getSuccessNotification(pMessage, pDelay);
    notification.show();
    return notification;
}

// ✅ Good - Internal helper functions (not exported)
function makeAlert(pType: AlertType, pMessage?: string, pDelay: number | false = false): Alert {
    let config = { ...urlParameters[pType] };
    config.delay = pDelay;
    return { content: pMessage, config: config };
}
```

### Default Parameters
```typescript
// ✅ Good - Default parameter values
export function getSuccessNotification(
    pMessage?: string,
    pDelay: number | false = false
): Noty {
    let alert = makeAlert(AlertType.Success, pMessage, pDelay);
    return getNotification(alert);
}
```

---

## jQuery Integration

### Type jQuery Elements
```typescript
// ✅ Good - Type jQuery selections
let btnAction: JQuery = $(submitFormElementSelector);
let form: JQuery = $(`#${formId}`);

btnAction.on("click", function (e: JQueryEventObject) {
    // Handle click
});
```

### Validation Integration
```typescript
// ✅ Good - Type validators
$("form").on("submit", function () {
    let validator = <JQueryValidation.Validator>$(this).data("validator");

    if (validator) {
        validator.settings.ignore = "";
        validator.settings.highlight = (element) =>
            $(element).closest(".form-group").addClass("has-error");
        validator.settings.unhighlight = (element) =>
            $(element).closest(".form-group").removeClass("has-error");
    }
});
```

---

## Error Handling

### Return null for Not Found
```typescript
// ✅ Good - Return null when not found
function searchFirstAlert(): Alert {
    for (let key in urlParameters) {
        let config: AlertConfig = { ...urlParameters[key] };
        let parameterValue = UrlManager.searchParameter(config.parameterName);

        if (parameterValue) {
            return { config: config, content: parameterValue };
        }
    }

    return null;  // Return null when not found
}
```

---

## Security

### Sanitize User Input
```typescript
// ✅ Good - Sanitize against HTML injection
export function sanitizeMessage(pMessage: string): string {
    // Sanitation against HTML Injection GITHUB TICKET SF-4929
    return pMessage.replace(/</g, "").replace(/>/g, "").replace("\"", "");
}

// ✅ Good - Option to use pre-sanitized content
function getNotification(pAlert: Alert, pIsSanitationAlreadyDone: boolean = false): Noty {
    let properText: string;
    if (pIsSanitationAlreadyDone === true) {
        properText = pAlert.content;
    } else {
        properText = sanitizeMessage(pAlert.content);
    }
    // ...
}
```

---

## Initialization Pattern

### Auto-execute Initialization
```typescript
// Define functions and classes
function handleUrlAlerts() {
    // Implementation
}

export function init() {
    // Initialization logic
}

// Auto-execute on module load
handleUrlAlerts();
```

---

## Configuration Objects

### Use Readonly Config Objects
```typescript
// ✅ Good - Configuration as const object
const urlParameters: { [type: number]: AlertConfig } = {
    [AlertType.Success]: {
        type: AlertType.Success,
        parameterName: "successMessage",
        className: "success",
        delay: 3000
    },
    [AlertType.Warning]: {
        type: AlertType.Warning,
        parameterName: "warningMessage",
        className: "warning",
        delay: 3000
    },
    [AlertType.Error]: {
        type: AlertType.Error,
        parameterName: "errorMessage",
        className: "danger",
        delay: false
    }
};
```

---

## Best Practices

### Spread Operator for Copying
```typescript
// ✅ Good - Use spread to copy
let config = { ...urlParameters[pType] };
config.delay = pDelay;
```

### Template Literals
```typescript
// ✅ Good - Template literals for string interpolation
let form = $(`#${formId}`);
this.barDom.innerHTML = `<div class="noty_body alert alert-${pAlert.config.className}">${this.options.text}</div>`;
```

### Strict Equality
```typescript
// ✅ Good - Use strict equality
if (pIsSanitationAlreadyDone === true) {
    properText = pAlert.content;
}
```

---

## Comments

### Document Complex Logic
```typescript
// ✅ Good - Explain non-obvious code
// Important: .noty_body class is required for setText API method.
this.barDom.innerHTML = `<div class="noty_body alert alert-${pAlert.config.className}">${this.options.text}</div>`;
```

### Reference Tickets
```typescript
// ✅ Good - Reference GITHUB tickets for context
// Sanitation against HTML Injection GITHUB TICKET SF-4929
return pMessage.replace(/</g, "").replace(/>/g, "").replace("\"", "");
```

---

**These conventions ensure consistency across the TypeScript codebase.**
