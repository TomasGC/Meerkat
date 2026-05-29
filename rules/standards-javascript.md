---
paths:
  - "**/*.js"
  - "**/*.mjs"
  - "**/cypress/**/*.js"
  - "**/*.bruno"
---

# JavaScript Standards

Modern JavaScript (ES6+) standards for Cypress tests, Bruno API tests, and general scripting.

**Applies to**: Cypress tests, Bruno collections, build scripts, Node.js utilities

---

## Language Version

### Use Modern ES6+ Features

```javascript
// ✅ Good - Modern syntax
const user = { name: 'John', age: 30 };
const { name, age } = user;
const isAdult = age >= 18;
const greeting = `Hello, ${name}!`;

// ❌ Bad - Old ES5 syntax
var user = { name: 'John', age: 30 };
var name = user.name;
var age = user.age;
var isAdult = age >= 18;
var greeting = 'Hello, ' + name + '!';
```

---

## Variable Declaration

### No `var` - Use `const` and `let`

```javascript
// ✅ Good - const for immutable, let for mutable
const API_URL = 'https://api.example.com';
let counter = 0;
counter++;

// ❌ Bad - var has function scope issues
var API_URL = 'https://api.example.com';
var counter = 0;
```

**Rule**: Default to `const`, only use `let` when reassignment needed.

---

## Functions

### Prefer Arrow Functions

```javascript
// ✅ Good - Arrow functions
const add = (a, b) => a + b;
const users = data.map(user => user.name);
const filtered = items.filter(item => item.active);

// ✅ Good - Traditional function when `this` context needed
function User(name) {
    this.name = name;
    this.greet = function() {
        return `Hello, ${this.name}`;
    };
}

// ❌ Bad - Verbose traditional syntax when arrow sufficient
const add = function(a, b) {
    return a + b;
};
```

### Async/Await over Promises

```javascript
// ✅ Good - async/await
async function getUser(id) {
    try {
        const response = await fetch(`/api/users/${id}`);
        const user = await response.json();
        return user;
    } catch (error) {
        console.error('Failed to fetch user:', error);
        throw error;
    }
}

// ❌ Bad - Promise chains
function getUser(id) {
    return fetch(`/api/users/${id}`)
        .then(response => response.json())
        .then(user => user)
        .catch(error => {
            console.error('Failed to fetch user:', error);
            throw error;
        });
}
```

---

## Objects and Arrays

### Object Destructuring

```javascript
// ✅ Good - Destructuring
const { name, email, age } = user;
const { data: users, status } = response;

// ❌ Bad - Manual extraction
const name = user.name;
const email = user.email;
const age = user.age;
```

### Spread Operator

```javascript
// ✅ Good - Spread for copying/merging
const newUser = { ...user, age: 31 };
const allItems = [...items1, ...items2];

// ❌ Bad - Object.assign or array concat
const newUser = Object.assign({}, user, { age: 31 });
const allItems = items1.concat(items2);
```

### Template Literals

```javascript
// ✅ Good - Template literals
const message = `User ${name} is ${age} years old`;
const html = `
    <div class="user">
        <h1>${name}</h1>
        <p>${email}</p>
    </div>
`;

// ❌ Bad - String concatenation
const message = 'User ' + name + ' is ' + age + ' years old';
```

---

## Cypress Testing Standards

### Test Structure

```javascript
describe('User Management', () => {
    beforeEach(() => {
        cy.visit('/users');
        cy.login('admin@example.com', 'password');
    });

    it('should create new user', () => {
        cy.get('[data-cy=new-user-btn]').click();
        cy.get('[data-cy=name-input]').type('John Doe');
        cy.get('[data-cy=email-input]').type('john@example.com');
        cy.get('[data-cy=submit-btn]').click();

        cy.contains('User created successfully').should('be.visible');
        cy.get('[data-cy=user-list]').should('contain', 'John Doe');
    });

    it('should validate email format', () => {
        cy.get('[data-cy=new-user-btn]').click();
        cy.get('[data-cy=email-input]').type('invalid-email');
        cy.get('[data-cy=submit-btn]').click();

        cy.contains('Invalid email format').should('be.visible');
    });
});
```

### Custom Commands

```javascript
// cypress/support/commands.js
Cypress.Commands.add('login', (email, password) => {
    cy.session([email, password], () => {
        cy.visit('/login');
        cy.get('[data-cy=email]').type(email);
        cy.get('[data-cy=password]').type(password);
        cy.get('[data-cy=submit]').click();
        cy.url().should('include', '/dashboard');
    });
});

Cypress.Commands.add('createUser', (userData) => {
    return cy.request({
        method: 'POST',
        url: '/api/users',
        body: userData,
        headers: {
            'Authorization': `Bearer ${Cypress.env('authToken')}`
        }
    });
});
```

### Best Practices

```javascript
// ✅ Good - Use data-cy attributes
cy.get('[data-cy=submit-btn]').click();

// ❌ Bad - Brittle selectors
cy.get('.btn.btn-primary.submit').click();
cy.get('button:nth-child(3)').click();

// ✅ Good - Wait for assertions
cy.get('[data-cy=user-list]').should('exist').and('be.visible');

// ❌ Bad - Arbitrary waits
cy.wait(3000);
cy.get('[data-cy=user-list]');
```

---

## Bruno API Testing Standards

### Collection Structure

```javascript
// bruno.json
{
    "name": "API Tests",
    "version": "1.0.0",
    "baseUrl": "{{baseUrl}}"
}
```

### Request Examples

**GET Request**:
```javascript
meta {
  name: Get User
  type: http
  seq: 1
}

get {
  url: {{baseUrl}}/api/users/{{userId}}
  auth: bearer
}

auth:bearer {
  token: {{authToken}}
}

tests {
  test("Status is 200", function() {
    expect(res.status).to.equal(200);
  });

  test("Response has user data", function() {
    expect(res.body).to.have.property('name');
    expect(res.body).to.have.property('email');
  });

  test("Email format is valid", function() {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    expect(res.body.email).to.match(emailRegex);
  });
}
```

**POST Request**:
```javascript
meta {
  name: Create User
  type: http
  seq: 2
}

post {
  url: {{baseUrl}}/api/users
  auth: bearer
  body: json
}

auth:bearer {
  token: {{authToken}}
}

body:json {
  {
    "name": "John Doe",
    "email": "john@example.com",
    "role": "user"
  }
}

tests {
  test("Status is 201", function() {
    expect(res.status).to.equal(201);
  });

  test("User ID is returned", function() {
    expect(res.body).to.have.property('id');
    expect(res.body.id).to.be.a('number');
  });

  // Store ID for subsequent requests
  bru.setEnvVar('createdUserId', res.body.id);
}
```

### Environment Variables

```javascript
// environments/local.bru
vars {
  baseUrl: http://localhost:3000
  authToken: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
}

vars:secret [
  authToken
]
```

---

## Error Handling

### Try-Catch for Async

```javascript
// ✅ Good - Comprehensive error handling
async function fetchUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch user:', error);
        // Re-throw or handle appropriately
        throw error;
    }
}

// ❌ Bad - No error handling
async function fetchUserData(userId) {
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
}
```

### Custom Error Classes

```javascript
class ValidationError extends Error {
    constructor(message, field) {
        super(message);
        this.name = 'ValidationError';
        this.field = field;
    }
}

class APIError extends Error {
    constructor(message, statusCode, response) {
        super(message);
        this.name = 'APIError';
        this.statusCode = statusCode;
        this.response = response;
    }
}

// Usage
if (!email.includes('@')) {
    throw new ValidationError('Invalid email format', 'email');
}
```

---

## Module System

### ES Modules (Preferred)

```javascript
// ✅ Good - ES modules
import { fetchUser, createUser } from './api/users.js';
import config from './config.js';

export const API_URL = 'https://api.example.com';
export default function handleRequest(data) {
    // Implementation
}
```

### CommonJS (Legacy - Node.js only)

```javascript
// ✅ Acceptable for Node.js compatibility
const { fetchUser } = require('./api/users');
const config = require('./config');

module.exports = {
    API_URL: 'https://api.example.com',
    handleRequest: function(data) {
        // Implementation
    }
};
```

---

## Best Practices

### No Callback Hell - Use Async/Await

```javascript
// ✅ Good
async function processOrder(orderId) {
    const order = await fetchOrder(orderId);
    const payment = await processPayment(order);
    const shipment = await createShipment(order, payment);
    return shipment;
}

// ❌ Bad - Callback hell
function processOrder(orderId, callback) {
    fetchOrder(orderId, (err, order) => {
        if (err) return callback(err);
        processPayment(order, (err, payment) => {
            if (err) return callback(err);
            createShipment(order, payment, (err, shipment) => {
                if (err) return callback(err);
                callback(null, shipment);
            });
        });
    });
}
```

### Use Array Methods

```javascript
// ✅ Good - Functional array methods
const activeUsers = users.filter(u => u.active);
const userNames = users.map(u => u.name);
const totalAge = users.reduce((sum, u) => sum + u.age, 0);
const hasAdmin = users.some(u => u.role === 'admin');
const allActive = users.every(u => u.active);

// ❌ Bad - Imperative loops
const activeUsers = [];
for (let i = 0; i < users.length; i++) {
    if (users[i].active) {
        activeUsers.push(users[i]);
    }
}
```

### Optional Chaining and Nullish Coalescing

```javascript
// ✅ Good - Safe property access
const city = user?.address?.city ?? 'Unknown';
const count = data?.items?.length ?? 0;

// ❌ Bad - Manual null checks
const city = user && user.address && user.address.city ? user.address.city : 'Unknown';
```

---

**These standards ensure modern, maintainable JavaScript code.**
