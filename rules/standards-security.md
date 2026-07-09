---
paths:
  - "**/*.cs"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.go"
  - "**/*.py"
  - "**/*.java"
  - "**/*.kt"
  - "**/*.rs"
  - "**/*.cshtml"
  - "**/*.razor"
---

# Company Security Standards

Security requirements for all projects using **ORCA Security**, **SonarQube**, and **OWASP Top 10**.

---

## Security Tools

### ORCA Security
**Purpose**: Cloud security platform for vulnerability scanning, compliance, and misconfiguration detection

**Coverage**:
- ✅ Container vulnerabilities (Docker images)
- ✅ Infrastructure misconfigurations (Azure, AWS)
- ✅ Compliance frameworks (PCI-DSS, GDPR, SOC2)
- ✅ Network security issues
- ✅ IAM misconfigurations
- ✅ Secret detection in code and configs

**Integration**:
- Automated scans on CI/CD pipeline
- Pre-deployment security gates
- Continuous monitoring in production
- Alert on Critical/High severity findings

### SonarQube / SonarCloud
**Purpose**: Continuous code quality and security analysis

**Coverage**:
- ✅ **Security Hotspots** - Potential security issues requiring review
- ✅ **Vulnerabilities** - Confirmed security flaws (injection, XSS, etc.)
- ✅ **Code Smells** - Maintainability issues
- ✅ **Bugs** - Reliability issues
- ✅ **Code Coverage** - Test coverage tracking
- ✅ **Technical Debt** - Estimated time to fix issues
- ✅ **Duplicated Code** - Code duplication detection

**Integration**:
- Runs on every PR (pull request)
- Quality Gate must pass before merge
- Automatic detection of new issues
- Tracks security rating (A-E)

**Quality Gate Requirements**:
- ✅ No new vulnerabilities
- ✅ No new bugs
- ✅ Security rating ≥ A
- ✅ Coverage on new code ≥ 80%
- ✅ Duplicated lines on new code < 3%
- ❌ No merge if Quality Gate fails

### OWASP Top 10
**Purpose**: Application security best practices for web applications

**Coverage**:
- ✅ Application-level vulnerabilities
- ✅ Code-level security issues
- ✅ Authentication/Authorization flaws
- ✅ Injection attacks
- ✅ XSS, CSRF, and other web attacks

---

## ORCA Security Compliance

### Before Deployment
```bash
# Run ORCA scan on Docker images
orca-cli scan image myapp:latest

# Check for Critical/High vulnerabilities
# Block deployment if Critical vulnerabilities found
```

### Required Checks
1. ✅ **No Critical vulnerabilities** in production images
2. ✅ **No High vulnerabilities** older than 30 days
3. ✅ **No exposed secrets** in containers or configs
4. ✅ **Compliance checks pass** (PCI-DSS, GDPR)
5. ✅ **No IAM misconfigurations** (overly permissive roles)

### Addressing ORCA Findings

#### Container Vulnerabilities
```dockerfile
# ✅ Good - Use minimal base images
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine

# ✅ Good - Multi-stage builds to reduce attack surface
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine
WORKDIR /app
COPY --from=build /app .

# ❌ Bad - Using full/outdated base images
FROM ubuntu:18.04
```

#### Update Dependencies Regularly
```bash
# Update base images
docker pull mcr.microsoft.com/dotnet/aspnet:8.0-alpine

# Update NuGet packages
dotnet list package --outdated
dotnet add package PackageName --version X.Y.Z

# Update npm packages
npm audit
npm audit fix
```

#### Secret Management
```yaml
# ❌ Bad - Secrets in environment variables
environment:
  - DATABASE_PASSWORD=MyP@ssw0rd
  - API_KEY=sk_live_1234567890

# ✅ Good - Use Azure Key Vault / AWS Secrets Manager
environment:
  - DATABASE_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:...
  - API_KEY_VAULT_URL=https://myvault.vault.azure.net/secrets/api-key
```

---

## OWASP Top 10 Compliance

All code must be checked against OWASP Top 10 vulnerabilities:

### 1. Broken Access Control
```csharp
// ❌ Bad - No authorization check
[HttpGet("{id}")]
public async Task<IActionResult> GetUser(int id)
{
    var user = await _userService.GetByIdAsync(id);
    return Ok(user);
}

// ✅ Good - Authorization enforced
[HttpGet("{id}")]
[Authorize]
public async Task<IActionResult> GetUser(int id)
{
    if (!User.CanAccessUser(id))
        return Forbid();

    var user = await _userService.GetByIdAsync(id);
    return Ok(user);
}
```

### 2. Cryptographic Failures
```csharp
// ❌ Bad - Weak hashing
var hash = MD5.HashData(Encoding.UTF8.GetBytes(password));

// ✅ Good - Strong hashing with salt
var hash = BCrypt.HashPassword(password, BCrypt.GenerateSalt(12));
```

### 3. Injection
```csharp
// ❌ Bad - SQL Injection vulnerability
var query = $"SELECT * FROM Users WHERE Email = '{email}'";

// ✅ Good - Parameterized query
var user = await _context.Users
    .FirstOrDefaultAsync(u => u.Email == email);
```

```typescript
// ❌ Bad - XSS vulnerability
element.innerHTML = userInput;

// ✅ Good - Sanitized input
element.textContent = userInput;
// Or use a sanitization library
```

### 4. Insecure Design
- ✅ Implement principle of least privilege
- ✅ Defense in depth (multiple security layers)
- ✅ Fail securely (deny by default)
- ✅ Validate all inputs
- ✅ Sanitize all outputs

### 5. Security Misconfiguration
```json
// ❌ Bad - Debug mode in production
{
  "Logging": {
    "LogLevel": {
      "Default": "Debug"
    }
  }
}

// ✅ Good - Appropriate logging level
{
  "Logging": {
    "LogLevel": {
      "Default": "Warning"
    }
  }
}
```

### 6. Vulnerable and Outdated Components
- ✅ Keep dependencies up to date
- ✅ Monitor security advisories
- ✅ Remove unused dependencies
- ✅ Use tools like Dependabot, Snyk

### 7. Identification and Authentication Failures
```csharp
// ✅ Password requirements
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Password history (prevent reuse)
- Account lockout after failed attempts
- MFA for sensitive operations
```

### 8. Software and Data Integrity Failures
- ✅ Use code signing
- ✅ Verify package integrity (checksums)
- ✅ Implement CI/CD pipeline security
- ✅ Use trusted registries only

### 9. Security Logging and Monitoring Failures
```csharp
// ✅ Good - Log security events
_logger.LogWarning(
    "Failed login attempt for user {Email} from IP {IP}",
    email,
    httpContext.Connection.RemoteIpAddress
);

_logger.LogInformation(
    "User {UserId} accessed sensitive resource {Resource}",
    userId,
    resourceId
);
```

### 10. Server-Side Request Forgery (SSRF)
```csharp
// ❌ Bad - User controls URL
var url = Request.Query["url"];
var response = await _httpClient.GetAsync(url);

// ✅ Good - Whitelist allowed domains
var allowedDomains = new[] { "api.trusted.com", "cdn.trusted.com" };
if (!allowedDomains.Any(d => url.Contains(d)))
    return BadRequest("Invalid URL");
```

---

## Sensitive Data Protection

### No Secrets in Code
```csharp
// ❌ Bad - Hardcoded credentials
var connectionString = "Server=prod;User=admin;Password=P@ssw0rd";
var apiKey = "sk_live_1234567890abcdef";

// ✅ Good - Environment variables or secure vault
var connectionString = _configuration["ConnectionStrings:Default"];
var apiKey = _configuration["ApiKeys:Stripe"];
```

### No Secrets in Logs
```csharp
// ❌ Bad - Logging sensitive data
_logger.LogInformation("Processing payment with card {CardNumber}", cardNumber);

// ✅ Good - Mask sensitive data
_logger.LogInformation("Processing payment with card ****{Last4}", cardLast4);
```

### Encryption Requirements
```csharp
// ✅ Encryption at rest
- Database: Transparent Data Encryption (TDE)
- Files: AES-256 encryption
- Backups: Encrypted backups only

// ✅ Encryption in transit
- TLS 1.3 minimum
- No self-signed certificates in production
- HTTPS everywhere
```

---

## Input Validation

### Validate All User Input
```csharp
// ✅ Good - Validate input
public async Task<IActionResult> CreateUser(CreateUserRequest request)
{
    if (!ModelState.IsValid)
        return BadRequest(ModelState);

    // Additional business validation
    if (await _userService.EmailExistsAsync(request.Email))
        return BadRequest("Email already exists");

    // Process
}
```

### Sanitize Output
```csharp
// ✅ Good - HTML encode output
@Html.Encode(Model.UserInput)

// ✅ Good - Use Anti-XSS libraries
var sanitized = HtmlSanitizer.Sanitize(userInput);
```

---

## Authentication & Authorization

### JWT Token Security
```csharp
// ✅ Token requirements
- Short-lived access tokens (15 minutes)
- Refresh tokens with rotation
- Secure token storage (httpOnly cookies or secure storage)
- Token revocation mechanism
```

### Role-Based Access Control (RBAC)
```csharp
// ✅ Good - Check permissions
[Authorize(Roles = "Admin,Manager")]
public async Task<IActionResult> DeleteUser(int id)
{
    // Implementation
}

// ✅ Better - Check specific permissions
[Authorize(Policy = "CanDeleteUsers")]
public async Task<IActionResult> DeleteUser(int id)
{
    // Implementation
}
```

---

## API Security

### Rate Limiting
```csharp
// ✅ Implement rate limiting
services.AddRateLimiter(options =>
{
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(context =>
        RateLimitPartition.GetFixedWindowLimiter(
            partitionKey: context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
            factory: _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 100,
                Window = TimeSpan.FromMinutes(1)
            }));
});
```

### CORS Configuration
```csharp
// ❌ Bad - Allow all origins
app.UseCors(builder => builder.AllowAnyOrigin());

// ✅ Good - Whitelist specific origins
app.UseCors(builder => builder
    .WithOrigins("https://trusted-domain.com")
    .AllowCredentials()
    .WithMethods("GET", "POST")
    .WithHeaders("Content-Type", "Authorization"));
```

### Request Size Limits
```csharp
// ✅ Set request size limits
[RequestSizeLimit(10_000_000)] // 10 MB
public async Task<IActionResult> UploadFile(IFormFile file)
{
    // Implementation
}
```

---

## Secure Coding Practices

### Use Prepared Statements
```csharp
// ✅ Always use parameterized queries or ORMs
var users = await _context.Users
    .Where(u => u.Email == email)
    .ToListAsync();
```

### Avoid Path Traversal
```csharp
// ❌ Bad - Path traversal vulnerability
var filePath = Path.Combine(uploadsPath, fileName);

// ✅ Good - Validate filename
if (fileName.Contains("..") || Path.IsPathRooted(fileName))
    return BadRequest("Invalid filename");

var safeFileName = Path.GetFileName(fileName);
var filePath = Path.Combine(uploadsPath, safeFileName);
```

### Implement CSRF Protection
```cshtml
@* ✅ Use anti-forgery tokens *@
<form asp-action="Create" method="post">
    @Html.AntiForgeryToken()
    @* Form fields *@
</form>
```

---

## Security Headers

### Required HTTP Headers
```csharp
// ✅ Security headers
app.Use(async (context, next) =>
{
    context.Response.Headers.Add("X-Frame-Options", "DENY");
    context.Response.Headers.Add("X-Content-Type-Options", "nosniff");
    context.Response.Headers.Add("X-XSS-Protection", "1; mode=block");
    context.Response.Headers.Add("Referrer-Policy", "no-referrer");
    context.Response.Headers.Add("Content-Security-Policy", "default-src 'self'");
    await next();
});
```

---

## Dependency Security

### Regular Security Audits
```bash
# .NET
dotnet list package --vulnerable

# Node.js
npm audit

# Go
go list -json -m all | nancy sleuth
```

### Auto-update Security Patches
- ✅ Use Dependabot or similar
- ✅ Review and test updates
- ✅ Apply critical patches immediately

---

## Incident Response

### Security Logging
```csharp
// ✅ Log security-relevant events
- Failed login attempts
- Access to sensitive resources
- Permission changes
- Configuration changes
- Unusual patterns
```

### Monitoring & Alerting
- ✅ Monitor for suspicious activity
- ✅ Alert on security events
- ✅ Have incident response plan
- ✅ Regular security reviews

---

## SonarQube Analysis

### Running Sonar Scan

**.NET Projects**:
```bash
# Begin analysis
dotnet sonarscanner begin \
  /k:"project-key" \
  /d:sonar.host.url="https://sonarcloud.io" \
  /d:sonar.login="YOUR_TOKEN" \
  /d:sonar.cs.opencover.reportsPaths="**/coverage.opencover.xml"

# Build and test
dotnet build
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=opencover

# End analysis
dotnet sonarscanner end /d:sonar.login="YOUR_TOKEN"
```

**Node.js Projects**:
```bash
# Install scanner
npm install -D sonarqube-scanner

# Run analysis
npx sonar-scanner \
  -Dsonar.projectKey=project-key \
  -Dsonar.sources=src \
  -Dsonar.host.url=https://sonarcloud.io \
  -Dsonar.login=YOUR_TOKEN \
  -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info
```

**Go Projects**:
```bash
sonar-scanner \
  -Dsonar.projectKey=project-key \
  -Dsonar.sources=. \
  -Dsonar.host.url=https://sonarcloud.io \
  -Dsonar.login=YOUR_TOKEN \
  -Dsonar.go.coverage.reportPaths=coverage.out
```

### Addressing Sonar Issues

#### Security Hotspots
```csharp
// ❌ Bad - Sonar flags weak cryptography
var hash = MD5.Create().ComputeHash(data);

// ✅ Good - Use strong cryptography
var hash = SHA256.Create().ComputeHash(data);
// Or better: use BCrypt for passwords
```

#### Vulnerabilities
```csharp
// ❌ Bad - SQL Injection (Sonar Critical)
var query = $"SELECT * FROM Users WHERE Email = '{email}'";

// ✅ Good - Parameterized query
var user = await _context.Users
    .FirstOrDefaultAsync(u => u.Email == email);
```

```typescript
// ❌ Bad - XSS vulnerability (Sonar Critical)
element.innerHTML = userInput;

// ✅ Good - Sanitized
element.textContent = userInput;
```

#### Code Smells
```csharp
// ❌ Bad - Cognitive complexity too high
public void ProcessOrder(Order order)
{
    if (order != null)
    {
        if (order.Items.Count > 0)
        {
            foreach (var item in order.Items)
            {
                if (item.Quantity > 0)
                {
                    if (item.Price > 0)
                    {
                        // ... deeply nested logic
                    }
                }
            }
        }
    }
}

// ✅ Good - Refactored for clarity
public void ProcessOrder(Order order)
{
    if (!IsValidOrder(order))
        return;

    foreach (var item in GetValidItems(order))
    {
        ProcessItem(item);
    }
}

private bool IsValidOrder(Order order)
{
    return order != null && order.Items.Any();
}

private IEnumerable<OrderItem> GetValidItems(Order order)
{
    return order.Items.Where(i => i.Quantity > 0 && i.Price > 0);
}
```

### Sonar Quality Profile

**Configure .sonarqube/project.properties**:
```properties
# Project identification
sonar.projectKey=mycompany:my-project
sonar.projectName=My Project
sonar.projectVersion=1.0

# Source code
sonar.sources=src
sonar.tests=tests

# Exclusions
sonar.exclusions=**/bin/**,**/obj/**,**/node_modules/**,**/wwwroot/lib/**
sonar.test.exclusions=**/*Tests/**

# Coverage
sonar.cs.opencover.reportsPaths=**/coverage.opencover.xml
sonar.javascript.lcov.reportPaths=coverage/lcov.info

# Language-specific
sonar.cs.analyzers=SonarAnalyzer.CSharp
sonar.typescript.node=node
```

---

## ORCA + Sonar + OWASP: Defense in Depth

### How They Complement Each Other

**ORCA Security** (Infrastructure & Platform):
- Scans container images for vulnerabilities
- Detects cloud misconfigurations (Azure/AWS)
- Monitors IAM permissions
- Checks compliance frameworks
- Finds exposed secrets in configs
- Network security analysis

**SonarQube** (Code Quality & Security):
- Static code analysis (SAST)
- Security hotspots in code
- Vulnerability detection (injection, XSS)
- Code smells and technical debt
- Code coverage tracking
- Duplicate code detection

**OWASP Top 10** (Application Security):
- Security principles and guidelines
- Authentication/Authorization patterns
- Input validation standards
- Output encoding practices
- Session management
- Secure coding practices

### Security Workflow

```
1. Developer writes code
   ↓
2. Sonar runs on commit (pre-commit hook optional)
   ↓
3. Code review (OWASP principles)
   ↓
4. Create Pull Request
   ↓
5. Sonar Quality Gate check
   ↓ (Fail = BLOCK merge)
6. Build Docker image
   ↓
7. ORCA scan (vulnerability check)
   ↓ (Critical/High = BLOCK)
8. Deploy to staging
   ↓
9. DAST tools (dynamic testing)
   ↓
10. Penetration testing (OWASP methodology)
   ↓
11. ORCA + Sonar continuous monitoring
   ↓
12. Production deployment
```

### Coverage Matrix

| Security Aspect | ORCA | Sonar | OWASP |
|----------------|------|-------|-------|
| Container vulnerabilities | ✅ | ❌ | ❌ |
| Cloud misconfigurations | ✅ | ❌ | ❌ |
| IAM permissions | ✅ | ❌ | ❌ |
| Secret detection | ✅ | ⚠️ | ❌ |
| Code vulnerabilities | ❌ | ✅ | ✅ |
| SQL Injection | ❌ | ✅ | ✅ |
| XSS | ❌ | ✅ | ✅ |
| CSRF | ❌ | ⚠️ | ✅ |
| Weak crypto | ❌ | ✅ | ✅ |
| Code quality | ❌ | ✅ | ❌ |
| Test coverage | ❌ | ✅ | ❌ |
| Technical debt | ❌ | ✅ | ❌ |

**Legend**: ✅ Full coverage | ⚠️ Partial coverage | ❌ Not covered

---

## ORCA Best Practices

### Container Security

#### Minimal Base Images
```dockerfile
# ✅ Good - Alpine for minimal attack surface
FROM node:20-alpine
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine

# ❌ Bad - Full distributions
FROM ubuntu:latest
FROM node:20
```

#### Non-Root User
```dockerfile
# ✅ Good - Run as non-root
FROM node:20-alpine

USER node
WORKDIR /app
COPY --chown=node:node . .

CMD ["node", "server.js"]

# ❌ Bad - Running as root
FROM node:20-alpine
WORKDIR /app
COPY . .
CMD ["node", "server.js"]
```

#### Read-Only Filesystem
```yaml
# ✅ Good - Read-only root filesystem
services:
  app:
    image: myapp:latest
    read_only: true
    tmpfs:
      - /tmp
      - /var/run

# ❌ Bad - Writable filesystem
services:
  app:
    image: myapp:latest
```

### Cloud Configuration Security

#### Azure Key Vault Integration
```csharp
// ✅ Good - Azure Key Vault
var keyVaultUrl = _configuration["KeyVault:Url"];
var credential = new DefaultAzureCredential();
var client = new SecretClient(new Uri(keyVaultUrl), credential);

var secret = await client.GetSecretAsync("DatabasePassword");
var connectionString = $"Server=...;Password={secret.Value.Value}";

// ❌ Bad - Hardcoded or environment variable
var password = "MyP@ssw0rd";
var password = Environment.GetEnvironmentVariable("DB_PASSWORD");
```

#### IAM Principle of Least Privilege
```json
// ✅ Good - Specific permissions only
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/uploads/*"
    }
  ]
}

// ❌ Bad - Wildcard permissions
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    }
  ]
}
```

### Network Security

#### Restrict Egress Traffic
```yaml
# ✅ Good - Whitelist allowed destinations
NetworkPolicy:
  egress:
    - to:
      - podSelector:
          matchLabels:
            app: database
      ports:
        - port: 5432

# ❌ Bad - Allow all egress
NetworkPolicy:
  egress:
    - {}
```

---

## Security Checklist

### Before Every Deployment

**Sonar Quality Gate**:
- [ ] Quality Gate status: PASSED
- [ ] No new vulnerabilities
- [ ] No new bugs
- [ ] Security rating ≥ A
- [ ] Coverage on new code ≥ 80%
- [ ] No security hotspots unreviewed
- [ ] Duplicated lines < 3%
- [ ] No code smells (Blocker/Critical)

**ORCA Checks**:
- [ ] No Critical vulnerabilities in images
- [ ] No High vulnerabilities > 30 days old
- [ ] No exposed secrets detected
- [ ] Compliance checks pass (PCI-DSS, GDPR)
- [ ] IAM permissions follow least privilege
- [ ] Network policies configured
- [ ] Base images up to date

**OWASP Checks**:
- [ ] Input validation on all endpoints
- [ ] Output encoding for user data
- [ ] Authentication/Authorization implemented
- [ ] CSRF protection enabled
- [ ] Security headers configured
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Secure session management
- [ ] Rate limiting configured

**Code Quality**:
- [ ] No hardcoded secrets in code
- [ ] No TODO/FIXME for security issues
- [ ] Error messages don't leak sensitive info
- [ ] Logging doesn't expose sensitive data
- [ ] All dependencies up to date
- [ ] No commented-out code
- [ ] Cognitive complexity < 15

---

## Reporting Security Issues

### If ORCA Alerts on Critical Issue
1. **Immediate action**: Stop deployment
2. **Assess impact**: Check if already in production
3. **Remediate**: Update vulnerable component
4. **Verify**: Re-run ORCA scan
5. **Document**: Update security log

### If You Discover OWASP Vulnerability
1. **Report immediately**: Create security issue (mark as confidential)
2. **Don't commit**: Don't push vulnerable code
3. **Fix first**: Address before continuing
4. **Review**: Have security team review fix
5. **Test**: Verify vulnerability is closed

---

**Security is everyone's responsibility. ORCA + OWASP = Strong defense. Report issues immediately.**
