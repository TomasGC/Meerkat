---
paths:
  - "**/*.sh"
  - "**/*.bash"
---

# Bash Scripting Standards

Shell scripting best practices for reliability and security.

---

## Script Header

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Description: Deploy application to staging
# Usage: ./deploy.sh <version>
# Author: DevOps Team
```

**Flags**:
- `-e` Exit on error
- `-u` Error on undefined variables
- `-o pipefail` Fail if any command in pipe fails

---

## Error Handling

```bash
# ✅ Good - Check command success
if ! command -v docker &> /dev/null; then
    echo "Error: docker not found" >&2
    exit 1
fi

# ✅ Good - Trap errors
cleanup() {
    echo "Cleaning up..."
    rm -f /tmp/deploy.lock
}
trap cleanup EXIT ERR

# ❌ Bad - Ignore errors
command_that_might_fail
continue_anyway
```

---

## Variables

```bash
# ✅ Good - Quote variables, use braces
readonly VERSION="${1:-1.0.0}"
readonly DEPLOY_DIR="/opt/myapp"
file_path="${DEPLOY_DIR}/config.json"

# ❌ Bad - Unquoted (word splitting issues)
VERSION=$1
file_path=$DEPLOY_DIR/config.json

# ✅ Good - Local variables in functions
deploy() {
    local version="$1"
    local target_dir="$2"
    echo "Deploying ${version} to ${target_dir}"
}
```

---

## Functions

```bash
# ✅ Good - Clear, testable functions
check_prerequisites() {
    command -v docker &> /dev/null || {
        echo "Error: docker not installed" >&2
        return 1
    }
    command -v kubectl &> /dev/null || {
        echo "Error: kubectl not installed" >&2
        return 1
    }
}

deploy_app() {
    local version="$1"
    echo "Deploying version ${version}..."
    docker build -t "myapp:${version}" . || return 1
    kubectl apply -f k8s/ || return 1
    echo "Deployment complete"
}

# Main
main() {
    check_prerequisites || exit 1
    deploy_app "${VERSION}" || exit 1
}

main "$@"
```

---

## Conditionals

```bash
# ✅ Good - Use [[ ]] for conditions
if [[ -f "${config_file}" ]]; then
    echo "Config found"
fi

if [[ "${env}" == "production" ]]; then
    echo "Production deploy"
fi

# ✅ Good - Check exit codes
if command_succeeds; then
    echo "Success"
else
    echo "Failed" >&2
    exit 1
fi

# ❌ Bad - Use [ ] (old syntax, less powerful)
if [ -f $config_file ]; then
    echo "Config found"
fi
```

---

## Loops

```bash
# ✅ Good - Iterate over array
services=("api" "web" "worker")
for service in "${services[@]}"; do
    echo "Deploying ${service}..."
    deploy_service "${service}"
done

# ✅ Good - Read file line by line
while IFS= read -r line; do
    process_line "${line}"
done < input.txt

# ❌ Bad - Word splitting issues
for file in $(ls *.txt); do
    process "$file"
done
```

---

## Input Validation

```bash
# ✅ Good - Validate arguments
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <version>" >&2
    exit 1
fi

readonly VERSION="$1"

if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format" >&2
    exit 1
fi
```

---

## Security

```bash
# ✅ Good - Use readonly for constants
readonly API_URL="https://api.example.com"
readonly MAX_RETRIES=3

# ✅ Good - Avoid eval
# ❌ Bad: eval "$user_input"
# ✅ Good: Use arrays or proper parsing

# ✅ Good - Secure temp files
temp_file=$(mktemp) || exit 1
trap 'rm -f "${temp_file}"' EXIT
echo "data" > "${temp_file}"
```

---

**Write robust, maintainable shell scripts.**
