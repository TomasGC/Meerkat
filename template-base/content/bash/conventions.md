## Bash Conventions

### Shebang & Safety

```bash
#!/usr/bin/env bash
set -euo pipefail  # exit on error, unbound var, pipe failure
```

### Naming

```bash
# Functions: snake_case
function get_user_by_id() { }
get_user_by_id()  # both syntaxes valid

# Variables: UPPER_SNAKE_CASE for globals/env, lower_snake_case for locals
readonly CONFIG_FILE="/etc/app/config.json"
local user_name="john"

# Constants: readonly
readonly MAX_RETRIES=3
```

### Variables

```bash
# ✅ Good - Quote all variables
echo "Hello, ${user_name}"
cp "${source_file}" "${dest_dir}/"

# ✅ Good - Default values
local timeout="${TIMEOUT:-30}"

# ✅ Good - Local variables in functions
function process_file() {
    local file_path="$1"
    local output_dir="$2"
}

# ❌ Bad - Unquoted variables (word splitting)
echo $user_name
cp $source $dest
```

### Error Handling

```bash
# ✅ Good - Check exit codes explicitly when needed
if ! command -v docker &>/dev/null; then
    echo "Error: docker is not installed" >&2
    exit 1
fi

# ✅ Good - Trap for cleanup
tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

# ✅ Good - Stderr for errors
echo "Error: file not found: ${file}" >&2
```

### Functions

```bash
# ✅ Good - Usage function, clear parameters
function deploy_service() {
    local service_name="$1"
    local environment="${2:-staging}"

    if [[ -z "${service_name}" ]]; then
        echo "Usage: deploy_service <service_name> [environment]" >&2
        return 1
    fi

    echo "Deploying ${service_name} to ${environment}..."
}

# ✅ Good - Return values via stdout
function get_latest_tag() {
    git describe --tags --abbrev=0
}
local tag
tag=$(get_latest_tag)
```

### Conditionals

```bash
# ✅ Good - [[ ]] over [ ]
if [[ "${status}" == "active" ]]; then
if [[ -f "${config_file}" ]]; then
if [[ "${count}" -gt 0 ]]; then

# ✅ Good - Case for multiple values
case "${environment}" in
    production) deploy_prod ;;
    staging)    deploy_staging ;;
    *)          echo "Unknown environment: ${environment}" >&2; exit 1 ;;
esac
```

### Script Structure

```bash
#!/usr/bin/env bash
set -euo pipefail

# Constants
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "$0")"

# Functions
function usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS] <arg>

Options:
  -h, --help     Show this help
  -v, --verbose  Verbose output
EOF
}

function main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help) usage; exit 0 ;;
            *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
        esac
        shift
    done
    # Main logic
}

main "$@"
```

### Testing (bats-core)

```bash
#!/usr/bin/env bats

setup() {
    load 'test_helper/bats-support/load'
    load 'test_helper/bats-assert/load'
    source "${BATS_TEST_DIRNAME}/../scripts/utils.sh"
}

@test "get_user_by_id returns user when found" {
    run get_user_by_id "123"
    assert_success
    assert_output --partial "john"
}

@test "deploy_service fails without service name" {
    run deploy_service ""
    assert_failure
    assert_output --partial "Usage:"
}
```

---
