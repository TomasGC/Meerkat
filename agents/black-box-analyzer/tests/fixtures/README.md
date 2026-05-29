# Test Fixtures for Universal Black-Box Analyzer

This directory contains test fixtures for all 19 supported project types.

## Fixtures Overview

### API Projects
- **go_project** (existing) - Go with Gin framework (REST API)

### CLI Projects
- **cli_project** - Go with Cobra CLI framework
  - Commands: `deploy`, `config set`
  - Flags: `--force`, `--environment`, `--key`, `--value`

### Mobile Projects
- **android_project** - Android with Kotlin + Jetpack Compose
  - Activities: `MainActivity`
  - Lifecycle methods: `onCreate`, `onStart`, `onResume`
  - UI handlers: `onButtonClick`
  - Composables: `UserScreen`

### Frontend Projects
- **frontend_project** - React with TypeScript
  - Components: `UserButton`, `UserList`
  - Hooks: `useState`, `useEffect`
  - Props: `userId`, `onClick`, `disabled`

### LLM/AI Projects
- **llm_agent_project** - LangChain agent system
  - Tools: `search_documents`, `calculate_risk`
  - Custom tools: `WebScraperTool`
  - Agents: `create_agent`
  - Prompts: `search_prompt`, `analysis_prompt`

### SQL Projects
- **sql_project** - PostgreSQL stored procedures
  - Procedures: `sp_CreateUser`
  - Functions: `fn_GetUserByEmail`, `fn_CalculateDiscount`
  - Triggers: `tr_UpdateTimestamp`, `tr_ValidateEmail`

### Event-Driven Projects

#### Serverless
- **serverless_project** - AWS Lambda (Python)
  - Handlers: `lambda_handler`, `scheduled_handler`, `sqs_handler`
  - Triggers: API Gateway, CloudWatch Events, SQS
  - Config: `serverless.yml`

#### Background Workers
- **worker_project** - Celery (Python)
  - Tasks: `send_email`, `process_payment`, `generate_report`, `cleanup_old_files`
  - Decorators: `@app.task`, `@shared_task`
  - Retry logic: `max_retries=3`

#### Message Queues
- **message_queue_project** - Kafka (Python)
  - Consumers: `process_user_event`
  - Producers: `publish_event`
  - Topics: `user-events`
  - Event types: `user.created`, `user.updated`, `user.deleted`

### Blockchain Projects
- **smart_contract_project** - Solidity (Ethereum)
  - Contract: `Token`
  - Functions: `transfer`, `approve`, `transferFrom`, `mint`, `burn`
  - Events: `Transfer`, `Approval`, `Mint`, `Burn`
  - Modifiers: `onlyOwner`, `validAddress`

### Hybrid Projects
- **hybrid_project** - Android + REST API (Go/Gin)
  - Mobile: `MainActivity` (Kotlin)
  - API: 3 endpoints (GET/POST /api/users)
  - Demonstrates multi-type detection

## Running Tests

### E2E Tests (All Fixtures)
```bash
cd ~/.claude/agents/black-box-analyzer
pytest tests/test_universal_detection.py -v
```

### Individual Fixture Analysis
```bash
# CLI project
python scripts/parallel_analyzer.py tests/fixtures/cli_project --verbose

# Android project
python scripts/parallel_analyzer.py tests/fixtures/android_project --verbose

# Frontend project
python scripts/parallel_analyzer.py tests/fixtures/frontend_project --verbose

# LLM agent project
python scripts/parallel_analyzer.py tests/fixtures/llm_agent_project --verbose

# SQL project
python scripts/parallel_analyzer.py tests/fixtures/sql_project --verbose

# Serverless project
python scripts/parallel_analyzer.py tests/fixtures/serverless_project --verbose

# Worker project
python scripts/parallel_analyzer.py tests/fixtures/worker_project --verbose

# Message queue project
python scripts/parallel_analyzer.py tests/fixtures/message_queue_project --verbose

# Smart contract project
python scripts/parallel_analyzer.py tests/fixtures/smart_contract_project --verbose

# Hybrid project
python scripts/parallel_analyzer.py tests/fixtures/hybrid_project --verbose
```

## Expected Results

### CLI Project
- **Detected types**: `cli_app`
- **Entry points**: 2+ commands (deploy, config set)
- **Scenarios**: Valid flags, missing flags, invalid values

### Android Project
- **Detected types**: `android_app`
- **Entry points**: 4+ (Activity + lifecycle + UI handlers)
- **Scenarios**: Lifecycle transitions, UI interactions

### Frontend Project
- **Detected types**: `frontend_react`
- **Entry points**: 2+ components (UserButton, UserList)
- **Scenarios**: Valid props, missing props, edge cases

### LLM Agent Project
- **Detected types**: `llm_ai_agent`
- **Entry points**: 3+ tools (search, calculate, scraper)
- **Scenarios**: Valid input, invalid schema, edge cases

### SQL Project
- **Detected types**: `sql_project`
- **Entry points**: 5+ (procedures + functions + triggers)
- **Scenarios**: Valid params, NULL values, constraint violations

### Serverless Project
- **Detected types**: `serverless`
- **Entry points**: 3+ handlers (API, scheduled, SQS)
- **Scenarios**: Valid events, timeouts, retries, DLQ

### Worker Project
- **Detected types**: `background_worker`
- **Entry points**: 4+ tasks
- **Scenarios**: Valid params, retries, failures, DLQ

### Message Queue Project
- **Detected types**: `message_queue`
- **Entry points**: 1+ consumers
- **Scenarios**: Valid messages, invalid schema, retries

### Smart Contract Project
- **Detected types**: `smart_contract`
- **Entry points**: 11+ (functions + events + modifiers)
- **Scenarios**: Valid calls, unauthorized, overflow, reentrancy

### Hybrid Project
- **Detected types**: `android_app`, `rest_api`, `hybrid`
- **Entry points**: Combined from both types
- **Scenarios**: Aggregated from both analyzers

## Fixture Maintenance

### Adding New Fixtures
1. Create directory: `tests/fixtures/<project-type>/`
2. Add minimal code with entry points
3. Add to `test_universal_detection.py`
4. Update this README

### Updating Fixtures
- Keep fixtures minimal (only what's needed for tests)
- Ensure all expected entry points are present
- Use realistic code patterns from actual projects

## Coverage Goals

Each fixture should demonstrate:
- ✅ Project type detection
- ✅ Entry point extraction
- ✅ Scenario generation
- ✅ Multi-analyzer support (for hybrid)

Current coverage: **10/19 project types** (52.6%)

Missing fixtures:
- Desktop (WPF, AppKit, Qt)
- Fullstack (Next.js, Remix, SvelteKit)
- iOS (Swift/SwiftUI)
- GraphQL API
- gRPC API
- Other mobile/desktop platforms

These can be added incrementally as needed.
