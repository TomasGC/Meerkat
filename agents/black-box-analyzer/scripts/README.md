# Black-Box-Analyzer Universal Scripts

**Universal automated test analysis for 19+ project types**

## Overview

This suite of Python 3.12+ scripts provides universal black-box test analysis for any codebase, automatically detecting project type and routing to appropriate analyzers.

### Supported Project Types (19)

| Category | Project Types |
|----------|---------------|
| **API** | REST API, GraphQL API, gRPC API |
| **CLI** | Command-line applications (Cobra, Click, argparse, Commander) |
| **Mobile** | Android (Kotlin/Java), iOS (Swift/SwiftUI) |
| **Desktop** | Windows (WPF, WinForms), macOS (AppKit), Linux (Qt, GTK) |
| **Frontend** | React, Vue, Angular |
| **Fullstack** | Next.js, Remix, SvelteKit |
| **AI/LLM** | LangChain agents, CrewAI, AutoGPT |
| **SQL** | PostgreSQL, SQL Server, MySQL (stored procedures, triggers) |
| **Event-Driven** | Serverless (Lambda, Azure Functions, Cloud Functions) |
| | Background workers (Celery, Sidekiq, Bull, asynq) |
| | Message queues (Kafka, RabbitMQ, SQS, Service Bus) |
| **Blockchain** | Smart contracts (Solidity, Rust/Solana, Move) |
| **Hybrid** | Multiple types in one project (e.g., Mobile + API) |

### Supported Languages (10+)

Go, TypeScript, JavaScript, C#, Python, Java, Ruby, Rust, Solidity, Move, Kotlin, Swift

## Architecture

### Universal Analyzer Pattern

```
┌─────────────────────────────────────────────────────────────┐
│              parallel_analyzer.py (Orchestrator)             │
│                      AnalyzerRouter                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         analyze_project_structure.py (Phase 0)               │
│              Multi-Type Detection Engine                     │
│                                                              │
│  Returns: project_types: [REST_API, ANDROID_APP, ...]      │
│           primary_type: ANDROID_APP                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              select_analyzers() (Phase 1)                    │
│          Route to Appropriate Analyzers                      │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│     MobileAnalyzer        │   │       APIAnalyzer         │
│  (extends BaseAnalyzer)   │   │  (extends BaseAnalyzer)   │
│                           │   │                           │
│  extract_entry_points()   │   │  extract_entry_points()   │
│  parse_tests()            │   │  parse_tests()            │
│  generate_scenarios()     │   │  generate_scenarios()     │
└───────────────────────────┘   └───────────────────────────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              aggregate_results() (Phase 5)                   │
│            Unified Coverage & Risk Analysis                  │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
scripts/
├── analyzers/                  # Universal analyzer system
│   ├── __init__.py
│   ├── base_analyzer.py       # Abstract base class
│   ├── api_analyzer.py        # REST/GraphQL/gRPC
│   ├── cli_analyzer.py        # CLI applications
│   ├── mobile_analyzer.py     # Android/iOS
│   ├── desktop_analyzer.py    # Windows/Mac/Linux
│   ├── frontend_analyzer.py   # React/Vue/Angular
│   ├── fullstack_analyzer.py  # Next.js/Remix/SvelteKit
│   ├── llm_analyzer.py        # LangChain/CrewAI agents
│   ├── sql_analyzer.py        # SQL projects
│   ├── event_driven/          # Event-driven package (DRY)
│   │   ├── base_event_driven_analyzer.py  # Shared patterns
│   │   ├── serverless_analyzer.py
│   │   ├── worker_analyzer.py
│   │   └── message_queue_analyzer.py
│   └── blockchain/
│       └── smart_contract_analyzer.py
│
├── common/
│   ├── models.py              # Universal data models
│   ├── constants.py           # Detection patterns
│   ├── utils.py               # File operations
│   └── cache.py               # Incremental cache
│
├── parallel_analyzer.py       # Main orchestrator
├── analyze_project_structure.py
├── parse_test_files.py        # Universal test parser
├── calculate_input_combinations.py
├── generate_coverage_matrix.py
├── prioritize_by_risk.py
└── diff_analysis.py
```

## Quick Start

### Universal Analysis (Automatic Type Detection)

```bash
# Analyze any project type (auto-detect)
python parallel_analyzer.py /path/to/project --verbose

# Output to JSON
python parallel_analyzer.py /path/to/project --output analysis.json

# Use 8 parallel workers
python parallel_analyzer.py /path/to/project --max-workers 8
```

### Example Outputs

#### Single-Type Project (REST API)
```json
{
  "success": true,
  "project_info": {
    "language": "go",
    "frameworks": ["gin"],
    "project_types": ["rest_api"],
    "primary_type": "rest_api"
  },
  "results": {
    "rest_api": {
      "entry_points": 42,
      "scenarios": 312,
      "coverage": {"coverage_percent": 67.8}
    }
  },
  "summary": {
    "total_entry_points": 42,
    "overall_coverage": 67.8
  }
}
```

#### Hybrid Project (Android + API)
```json
{
  "success": true,
  "project_info": {
    "project_types": ["android_app", "rest_api", "hybrid"],
    "primary_type": "android_app"
  },
  "results": {
    "android_app": {
      "entry_points": 23,
      "scenarios": 156,
      "coverage": {"coverage_percent": 45.2}
    },
    "rest_api": {
      "entry_points": 45,
      "scenarios": 312,
      "coverage": {"coverage_percent": 67.8}
    },
    "hybrid": {
      "entry_points": 68,
      "scenarios": 468,
      "coverage": {"coverage_percent": 56.5}
    }
  },
  "summary": {
    "total_entry_points": 68,
    "overall_coverage": 56.5
  }
}
```

## Data Models

### Universal Entry Point

```python
@dataclass
class EntryPoint:
    """Universal entry point (replaces API-only Endpoint).
    
    Represents any testable entry point:
    - HTTP endpoints: "/users/:id"
    - CLI commands: "deploy --force"
    - Mobile handlers: "MainActivity.onCreate"
    - Frontend components: "UserButton"
    - LLM tools: "search_documents"
    - SQL procedures: "sp_CreateUser"
    - Lambda handlers: "lambda_handler"
    - Smart contract functions: "Token.transfer"
    """
    type: EntryPointType
    name: str
    params: list[Parameter]
    file_path: str
    line_number: int
    framework: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Entry Point Types (30+)

```python
class EntryPointType(Enum):
    # API Entry Points
    HTTP_ENDPOINT = "http_endpoint"
    GRAPHQL_QUERY = "graphql_query"
    GRPC_METHOD = "grpc_method"
    
    # CLI Entry Points
    CLI_COMMAND = "cli_command"
    CLI_SUBCOMMAND = "cli_subcommand"
    CLI_FLAG = "cli_flag"
    
    # Mobile Entry Points
    ACTIVITY = "activity"
    FRAGMENT = "fragment"
    VIEW_CONTROLLER = "view_controller"
    LIFECYCLE_METHOD = "lifecycle_method"
    UI_HANDLER = "ui_handler"
    
    # Desktop Entry Points
    WINDOW = "window"
    EVENT_HANDLER = "event_handler"
    
    # Frontend Entry Points
    COMPONENT = "component"
    HOOK = "hook"
    ROUTE = "route"
    
    # AI/Agent Entry Points
    AGENT_TOOL = "agent_tool"
    AGENT_WORKFLOW = "agent_workflow"
    PROMPT_TEMPLATE = "prompt_template"
    
    # SQL Entry Points
    STORED_PROCEDURE = "stored_procedure"
    SQL_FUNCTION = "sql_function"
    SQL_TRIGGER = "sql_trigger"
    
    # Event-Driven Entry Points
    LAMBDA_HANDLER = "lambda_handler"
    FUNCTION_HANDLER = "function_handler"
    BACKGROUND_JOB = "background_job"
    MESSAGE_CONSUMER = "message_consumer"
    
    # Blockchain Entry Points
    SMART_CONTRACT_FUNCTION = "smart_contract_function"
    CONTRACT_EVENT = "contract_event"
    CONTRACT_MODIFIER = "contract_modifier"
```

## Usage Examples

### 1. Analyze CLI Application

```bash
python parallel_analyzer.py ~/my-cli-app --verbose
```

**Output**:
```
🔍 Phase 0: Detecting project types...
  ✅ Language: go
  ✅ Frameworks: cobra
  ✅ Project types: cli_app
  ✅ Primary type: cli_app

📊 Phase 1: Selecting analyzers...
  ✅ Using 1 analyzer(s):
     - CLIAnalyzer

🚀 Phase 2-4: Running analyzers (parallel)...
  ✅ CLIAnalyzer: 5 entry points, 35 scenarios

✅ Analysis complete!
   Total entry points: 5
   Total scenarios: 35
   Overall coverage: 42.8%
```

### 2. Analyze Android App

```bash
python parallel_analyzer.py ~/my-android-app --verbose
```

**Detects**:
- Activities, Fragments
- Lifecycle methods (onCreate, onStart, onResume)
- UI handlers (onClick, onLongClick)
- Jetpack Compose composables

### 3. Analyze LangChain Agent

```bash
python parallel_analyzer.py ~/my-llm-agent --verbose
```

**Detects**:
- @tool decorated functions
- BaseTool classes
- AgentExecutor workflows
- PromptTemplates

### 4. Analyze Smart Contract

```bash
python parallel_analyzer.py ~/my-token-contract --verbose
```

**Detects**:
- Public/external functions
- Events
- Modifiers
- Security scenarios (reentrancy, overflow)

### 5. Analyze Hybrid Project

```bash
python parallel_analyzer.py ~/my-fullstack-app --verbose
```

**Detects**:
- Multiple project types
- Routes to multiple analyzers
- Aggregates results

## Advanced Usage

### With Cache

```bash
# First run (builds cache)
python parallel_analyzer.py /path/to/project --verbose

# Second run (uses cache, much faster)
python parallel_analyzer.py /path/to/project --verbose
```

### Clear Cache

```bash
python parallel_analyzer.py /path/to/project --clear-cache
```

### Disable Cache

```bash
python parallel_analyzer.py /path/to/project --no-cache
```

### Custom Workers

```bash
# Use 16 parallel workers for large projects
python parallel_analyzer.py /path/to/project --max-workers 16
```

## Supported Frameworks by Type

### API Frameworks
- **Go**: gin, echo, fiber, chi, mux
- **TypeScript**: Express, NestJS, Fastify, Koa, Hapi
- **C#**: ASP.NET Core, Minimal APIs
- **Python**: FastAPI, Flask, Django, Starlette
- **Java**: Spring Boot, Quarkus, Micronaut

### CLI Frameworks
- **Go**: Cobra, urfave/cli, flags
- **Python**: Click, argparse, Typer
- **TypeScript**: Commander, Yargs
- **C#**: CommandLineParser
- **Java**: Picocli

### Mobile Frameworks
- **Android**: Jetpack Compose, View-based
- **iOS**: SwiftUI, UIKit

### Frontend Frameworks
- **React**: Function components, hooks, React Router
- **Vue**: Composition API, Options API, Vue Router
- **Angular**: Components, services, modules

### LLM Frameworks
- **LangChain**: Tools, agents, chains, prompts
- **CrewAI**: Agents, tasks, crews
- **AutoGPT**: Agent tools

### Event-Driven Frameworks
- **Serverless**: AWS Lambda, Azure Functions, Cloud Functions
- **Workers**: Celery, Sidekiq, Bull, asynq
- **Message Queues**: Kafka, RabbitMQ, SQS, Service Bus

### Blockchain Platforms
- **Ethereum**: Solidity
- **Solana**: Rust (Anchor framework)
- **Aptos/Sui**: Move

## Testing

### Run E2E Tests

```bash
cd ~/.claude/agents/black-box-analyzer
pytest tests/test_universal_detection.py -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov=scripts --cov-report=term-missing
```

### Test Individual Fixtures

```bash
# CLI project
python parallel_analyzer.py tests/fixtures/cli_project --verbose

# Android project
python parallel_analyzer.py tests/fixtures/android_project --verbose

# Frontend project
python parallel_analyzer.py tests/fixtures/frontend_project --verbose

# LLM agent project
python parallel_analyzer.py tests/fixtures/llm_agent_project --verbose

# Smart contract project
python parallel_analyzer.py tests/fixtures/smart_contract_project --verbose

# Hybrid project
python parallel_analyzer.py tests/fixtures/hybrid_project --verbose
```

## Performance

### Typical Analysis Times

| Project Size | Entry Points | Analysis Time | With Cache |
|--------------|--------------|---------------|------------|
| Small | 10-20 | 2-5 seconds | 0.5-1 second |
| Medium | 50-100 | 5-15 seconds | 1-3 seconds |
| Large | 200-500 | 15-45 seconds | 3-8 seconds |
| Very Large | 1000+ | 1-3 minutes | 10-30 seconds |

**Parallelization**: 3-5x faster than sequential execution

## Integration with Agent

The black-box-analyzer agent invokes these scripts:

```python
# In AGENT.md workflow
result = Bash({
    "command": "python ~/.claude/agents/black-box-analyzer/scripts/parallel_analyzer.py /path/to/project --output analysis.json",
    "description": "Analyze project with universal detection"
})
```

## Requirements

- **Python**: 3.12+
- **Dependencies**: See `requirements.txt`

```bash
pip install -r requirements.txt
```

## Contributing

### Adding New Project Type

1. Create analyzer in `analyzers/<name>_analyzer.py`
2. Extend `BaseAnalyzer` abstract class
3. Add detection patterns to `common/constants.py`
4. Add project type to `common/models.py`
5. Create test fixture in `tests/fixtures/<type>_project/`
6. Add E2E test to `tests/test_universal_detection.py`
7. Update this README

### Adding New Framework Support

1. Add detection pattern to `common/constants.py`
2. Add extraction logic to appropriate analyzer
3. Add test case to fixture
4. Update documentation

## License

Part of black-box-analyzer agent suite.
