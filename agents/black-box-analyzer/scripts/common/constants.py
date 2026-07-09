#!/usr/bin/env python3
"""Constants for black-box-analyzer scripts.

Framework patterns, regex, and configuration constants.
"""

import re

# Language detection patterns
LANGUAGE_INDICATORS = {
    "go": ["go.mod", "go.sum"],
    "typescript": ["tsconfig.json", "package.json"],
    "javascript": ["package.json"],
    "csharp": ["*.csproj", "*.sln"],
    "python": ["requirements.txt", "pyproject.toml", "setup.py"],
    "kotlin": ["build.gradle.kts", "*.kt"],
    "java": ["pom.xml", "build.gradle"],
    "ruby": ["Gemfile", "Gemfile.lock"],
    "php": ["composer.json"],
    "rust": ["Cargo.toml", "Cargo.lock"],
    "swift": ["Package.swift", "*.xcodeproj"],
    "cpp": ["CMakeLists.txt", "*.cpp", "*.hpp"],
}

# Framework detection patterns (in package files)
FRAMEWORK_PATTERNS = {
    # Go frameworks
    "gin": r"github\.com/gin-gonic/gin",
    "echo": r"github\.com/labstack/echo",
    "fiber": r"github\.com/gofiber/fiber",
    "chi": r"github\.com/go-chi/chi",
    "mux": r"github\.com/gorilla/mux",
    # TypeScript/Node frameworks
    "express": r'"express"',
    "nestjs": r'"@nestjs/core"',
    "fastify": r'"fastify"',
    "koa": r'"koa"',
    "hapi": r'"@hapi/hapi"',
    # Python frameworks
    "fastapi": r"fastapi",
    "flask": r"Flask",
    "django": r"Django",
    "starlette": r"starlette",
    # C# frameworks
    "aspnet": r"Microsoft\.AspNetCore",
    "entityframework": r"Microsoft\.EntityFrameworkCore",
    # Java frameworks
    "spring": r"org\.springframework",
    "quarkus": r"io\.quarkus",
    "micronaut": r"io\.micronaut",
}

# Test file patterns (glob patterns)
TEST_FILE_PATTERNS = {
    "go": ["*_test.go"],
    "typescript": ["*.test.ts", "*.spec.ts", "**/__tests__/**/*.ts"],
    "javascript": ["*.test.js", "*.spec.js", "**/__tests__/**/*.js"],
    "csharp": ["*.Tests.cs", "**/*Tests/**/*.cs"],
    "python": ["test_*.py", "*_test.py", "**/tests/**/*.py"],
    "java": ["*Test.java", "**/*Test.java", "**/test/**/*.java"],
    "ruby": ["*_spec.rb", "**/*_spec.rb"],
    "php": ["*Test.php", "**/*Test.php"],
    "kotlin": ["*Test.kt", "**/*Test.kt", "**/test/**/*.kt"],
    "rust": ["tests/**/*.rs"],
    "swift": ["*Tests.swift", "**/*Tests/**/*.swift"],
    "cpp": ["*_test.cpp", "*_test.cc", "**/*test*.cpp", "**/*test*.cc"],
}

# API endpoint detection patterns
ENDPOINT_PATTERNS = {
    # Go
    "go_gin": re.compile(
        r'router\.(GET|POST|PUT|PATCH|DELETE|OPTIONS)\s*\(\s*["\']([^"\']+)["\']'
    ),
    "go_echo": re.compile(
        r'e\.(GET|POST|PUT|PATCH|DELETE)\s*\(\s*["\']([^"\']+)["\']'
    ),
    "go_fiber": re.compile(
        r'app\.(Get|Post|Put|Patch|Delete)\s*\(\s*["\']([^"\']+)["\']'
    ),
    "go_chi": re.compile(
        r'r\.(Get|Post|Put|Patch|Delete)\s*\(\s*["\']([^"\']+)["\']'
    ),
    "go_mux": re.compile(
        r'router\.HandleFunc\s*\(\s*["\']([^"\']+)["\']\s*,.*\)\.Methods\s*\(\s*["\']([A-Z]+)["\']\s*\)'
    ),
    # TypeScript/JavaScript
    "ts_express": re.compile(
        r'app\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']'
    ),
    "ts_nestjs": re.compile(
        r'@(Get|Post|Put|Patch|Delete)\s*\(\s*["\']([^"\']*)["\']\s*\)'
    ),
    "ts_fastify": re.compile(
        r'fastify\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']'
    ),
    # Python
    "py_fastapi": re.compile(
        r'@app\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']'
    ),
    "py_flask": re.compile(
        r'@app\.route\s*\(\s*["\']([^"\']+)["\']\s*,\s*methods\s*=\s*\[["\']([A-Z]+)["\']\]'
    ),
    "py_django": re.compile(
        r'path\s*\(\s*["\']([^"\']+)["\']\s*,'
    ),
    # C#
    "cs_aspnet_attribute": re.compile(
        r'\[Http(Get|Post|Put|Patch|Delete)\s*\(\s*["\']([^"\']*)["\']\s*\)\]'
    ),
    "cs_aspnet_minimal": re.compile(
        r'app\.Map(Get|Post|Put|Patch|Delete)\s*\(\s*["\']([^"\']+)["\']'
    ),
    # Java
    "java_spring": re.compile(
        r'@(GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping)\s*\(\s*["\']([^"\']*)["\']\s*\)'
    ),
}

# Test framework detection patterns
TEST_FRAMEWORK_PATTERNS = {
    # Go
    "go_testing": re.compile(r"func\s+Test\w+\s*\(t\s+\*testing\.T\)"),
    # TypeScript/JavaScript
    "jest": re.compile(r'(describe|it|test)\s*\('),
    "vitest": re.compile(r'(describe|it|test)\s*\('),
    "mocha": re.compile(r'(describe|it)\s*\('),
    # Python
    "pytest": re.compile(r"def\s+test_\w+"),
    "unittest": re.compile(r"class\s+\w+\(unittest\.TestCase\)"),
    # C#
    "xunit": re.compile(r"\[Fact\]|\[Theory\]"),
    "nunit": re.compile(r"\[Test\]|\[TestCase\]"),
    "mstest": re.compile(r"\[TestMethod\]"),
    # Java
    "junit": re.compile(r"@Test"),
    "testng": re.compile(r"@Test"),
    "kotlin_kotest": re.compile(r"class\s+\w+\s*:\s*(StringSpec|FunSpec|BehaviorSpec|DescribeSpec|ShouldSpec)"),
    "rust_test": re.compile(r"#\[test\]"),
    "xctest": re.compile(r"class\s+\w+\s*:\s*XCTestCase|func\s+test\w+\(\s*\)"),
    "gtest": re.compile(r"TEST\s*\(|TEST_F\s*\("),
    "catch2": re.compile(r"TEST_CASE\s*\(|SECTION\s*\("),
}

# HTTP status codes
HTTP_STATUS_CODES = {
    # Success
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    # Client errors
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    # Server errors
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}

# Default response codes by method
DEFAULT_RESPONSE_CODES = {
    "GET": [200, 400, 401, 403, 404, 500],
    "POST": [201, 400, 401, 403, 409, 422, 500],
    "PUT": [200, 204, 400, 401, 403, 404, 422, 500],
    "PATCH": [200, 204, 400, 401, 403, 404, 422, 500],
    "DELETE": [204, 400, 401, 403, 404, 500],
}

# Edge case values for input combinations
EDGE_CASE_VALUES = {
    "string": [
        "",  # Empty
        " ",  # Whitespace
        None,  # Null
        "a" * 1000,  # Max length
        "<script>alert('xss')</script>",  # XSS
        "'; DROP TABLE users--",  # SQL injection
        "../../../etc/passwd",  # Path traversal
        "🎉💯🚀",  # Unicode/emoji
    ],
    "integer": [
        0,
        -1,
        1,
        2147483647,  # MAX_INT (32-bit)
        -2147483648,  # MIN_INT (32-bit)
        None,
    ],
    "float": [
        0.0,
        -1.0,
        1.0,
        3.14159,
        float("inf"),
        float("-inf"),
        None,
    ],
    "boolean": [True, False, None],
    "array": [
        [],  # Empty
        [1],  # Single element
        [1, 2, 3, 4, 5],  # Multiple
        [1, 1, 1],  # Duplicates
        None,
    ],
    "object": [
        {},  # Empty
        {"key": "value"},  # Valid
        {"extra": "field"},  # Extra fields
        None,
    ],
}

# Risk scoring thresholds
RISK_THRESHOLDS = {
    "CRITICAL": 60,
    "HIGH": 40,
    "MEDIUM": 20,
    "LOW": 0,
}

# File exclusions (don't parse these directories)
EXCLUDED_DIRS = {
    "node_modules",
    "vendor",
    "bin",
    "obj",
    "dist",
    "build",
    ".git",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "target",
}

# Common API path prefixes
API_PATH_PREFIXES = [
    "/api/",
    "/v1/",
    "/v2/",
    "/rest/",
    "/graphql",
    "/grpc",
]

# ====================
# UNIVERSAL PROJECT TYPE DETECTION PATTERNS
# ====================

# CLI detection patterns
CLI_PATTERNS = {
    # Go CLI frameworks
    "go_cobra": re.compile(r"cobra\.Command\{"),
    "go_flags": re.compile(r"flags\.StringVar\(|flag\.(String|Int|Bool)"),
    "go_cli": re.compile(r"urfave/cli"),
    # Python CLI frameworks
    "py_argparse": re.compile(r"argparse\.ArgumentParser\("),
    "py_click": re.compile(r"@click\.(command|group|option)"),
    "py_typer": re.compile(r"import typer|typer\.Typer\("),
    # TypeScript/JavaScript CLI
    "ts_commander": re.compile(r"program\.command\("),
    "ts_yargs": re.compile(r"yargs\.command\("),
    "ts_argv": re.compile(r"process\.argv"),
    # C# CLI
    "cs_commandline": re.compile(r"CommandLine\.Parser"),
    # Java CLI
    "java_picocli": re.compile(r"@Command\("),
}

# Mobile app detection patterns
MOBILE_PATTERNS = {
    # Android
    "android_activity": re.compile(r"class\s+\w+\s*:\s*Activity|class\s+\w+\s*:\s*AppCompatActivity"),
    "android_fragment": re.compile(r"class\s+\w+\s*:\s*Fragment"),
    "android_compose": re.compile(r"@Composable"),
    "android_lifecycle": re.compile(r"override\s+fun\s+(onCreate|onStart|onResume|onPause|onStop)"),
    "android_manifest": "AndroidManifest.xml",  # File indicator
    # iOS
    "ios_viewcontroller": re.compile(r"class\s+\w+\s*:\s*UIViewController"),
    "ios_swiftui": re.compile(r"struct\s+\w+\s*:\s*View"),
    "ios_lifecycle": re.compile(r"override\s+func\s+(viewDidLoad|viewWillAppear|viewDidAppear)"),
    "ios_ibaction": re.compile(r"@IBAction"),
    "ios_plist": "Info.plist",  # File indicator
}

# Desktop app detection patterns
DESKTOP_PATTERNS = {
    # Windows (WPF/WinForms)
    "wpf_window": re.compile(r"<Window\s.*xmlns"),
    "wpf_xaml": re.compile(r"\.xaml$"),
    "wpf_command": re.compile(r"ICommand|RelayCommand"),
    "wpf_click": re.compile(r"void\s+\w+_Click\("),
    "winforms_form": re.compile(r"class\s+\w+\s*:\s*Form"),
    # macOS (AppKit)
    "macos_nswindow": re.compile(r"class\s+\w+\s*:\s*NSWindowController"),
    "macos_ibaction": re.compile(r"@IBAction\s+func"),
    "macos_xib": re.compile(r"\.xib$"),
    # Linux (Qt/GTK)
    "qt_mainwindow": re.compile(r"class\s+\w+\s*:\s*public\s+QMainWindow"),
    "qt_signal": re.compile(r"connect\(.*SIGNAL|Q_OBJECT"),
    "gtk_window": re.compile(r"GtkWindow|gtk_window_"),
}

# Frontend framework detection patterns
FRONTEND_PATTERNS = {
    # React
    "react_component": re.compile(r"export\s+(default\s+)?function\s+\w+\(|const\s+\w+\s*=\s*\(\)\s*=>"),
    "react_hooks": re.compile(r"useState\(|useEffect\(|useContext\("),
    "react_router": re.compile(r"<Route\s+path="),
    "react_jsx": re.compile(r"return\s*\(?\s*<\w+"),
    # Vue
    "vue_template": re.compile(r"<template>"),
    "vue_setup": re.compile(r"setup\(\)"),
    "vue_composable": re.compile(r"defineProps\(|defineEmits\(|ref\(|computed\("),
    "vue_router": re.compile(r"<router-view|<router-link"),
    # Angular
    "angular_component": re.compile(r"@Component\("),
    "angular_input": re.compile(r"@Input\(\)"),
    "angular_output": re.compile(r"@Output\(\)"),
    "angular_router": re.compile(r"routerLink="),
    "angular_json": "angular.json",  # File indicator
}

# Fullstack framework detection patterns
FULLSTACK_PATTERNS = {
    # Next.js
    "nextjs_api": re.compile(r"export\s+(default\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)\("),
    "nextjs_page": re.compile(r"export\s+default\s+function\s+\w+\("),
    "nextjs_config": "next.config.js",  # File indicator
    # Remix
    "remix_loader": re.compile(r"export\s+(const\s+)?loader"),
    "remix_action": re.compile(r"export\s+(const\s+)?action"),
    "remix_config": "remix.config.js",  # File indicator
    # SvelteKit
    "sveltekit_load": re.compile(r"export\s+(const\s+)?load"),
    "sveltekit_actions": re.compile(r"export\s+(const\s+)?actions"),
    "sveltekit_config": "svelte.config.js",  # File indicator
}

# LLM/AI agent detection patterns
LLM_PATTERNS = {
    # LangChain
    "langchain_tool": re.compile(r"@tool|class\s+\w+\(BaseTool\)"),
    "langchain_agent": re.compile(r"AgentExecutor|initialize_agent"),
    "langchain_prompt": re.compile(r"PromptTemplate|ChatPromptTemplate"),
    "langchain_chain": re.compile(r"LLMChain|SequentialChain"),
    # CrewAI
    "crewai_agent": re.compile(r"@agent|class\s+\w+\(Agent\)"),
    "crewai_task": re.compile(r"@task|class\s+\w+\(Task\)"),
    "crewai_crew": re.compile(r"Crew\("),
    # AutoGPT / General
    "autogpt_agent": re.compile(r"AutoGPT|GPTAgent"),
    "agent_tool": re.compile(r"def\s+\w+_tool\(|class\s+\w+Tool"),
}

# SQL project detection patterns
SQL_PATTERNS = {
    # PostgreSQL
    "postgres_procedure": re.compile(r"CREATE\s+(OR\s+REPLACE\s+)?(PROCEDURE|FUNCTION)", re.IGNORECASE),
    "postgres_trigger": re.compile(r"CREATE\s+TRIGGER", re.IGNORECASE),
    # SQL Server
    "sqlserver_procedure": re.compile(r"CREATE\s+(OR\s+ALTER\s+)?(PROC|PROCEDURE)", re.IGNORECASE),
    "sqlserver_function": re.compile(r"CREATE\s+(OR\s+ALTER\s+)?FUNCTION", re.IGNORECASE),
    # MySQL
    "mysql_procedure": re.compile(r"CREATE\s+PROCEDURE", re.IGNORECASE),
    "mysql_function": re.compile(r"CREATE\s+FUNCTION", re.IGNORECASE),
    # General SQL
    "sql_file": re.compile(r"\.sql$"),
}

# Serverless function detection patterns
SERVERLESS_PATTERNS = {
    # AWS Lambda
    "aws_lambda_python": re.compile(r"def\s+(lambda_handler)\s*\(event,\s*context\)"),
    "aws_lambda_node": re.compile(r"exports\.(handler|lambdaHandler)\s*="),
    "aws_lambda_go": re.compile(r"func\s+handler\s*\(.*events\."),
    # Azure Functions
    "azure_function": re.compile(r"@app\.(route|function_name)\(|FunctionName\("),
    # Google Cloud Functions
    "gcp_function": re.compile(r"@functions_framework\.|exports\.\w+\s*=\s*\(req,\s*res\)"),
}

# Background job / worker detection patterns
WORKER_PATTERNS = {
    # Python - Celery
    "celery_task": re.compile(r"@(?:app|celery)\.task|@shared_task"),
    "celery_app": re.compile(r"Celery\s*\("),
    # Ruby - Sidekiq
    "sidekiq_worker": re.compile(r"class\s+\w+\s*include\s+Sidekiq::Worker"),
    "sidekiq_perform": re.compile(r"def\s+perform\s*\("),
    # Node.js - Bull
    "bull_queue": re.compile(r"new\s+Queue\(|queue\.process\("),
    # Go - asynq
    "asynq_handler": re.compile(r"asynq\.HandlerFunc\("),
}

# Message queue detection patterns
MESSAGE_QUEUE_PATTERNS = {
    # Kafka
    "kafka_consumer": re.compile(r"kafka\.Consumer\(|@kafka\.consumer|KafkaConsumer\("),
    "kafka_producer": re.compile(r"kafka\.Producer\(|KafkaProducer\("),
    # RabbitMQ
    "rabbitmq_consume": re.compile(r"channel\.consume\(|basic_consume\(|@RabbitListener"),
    # AWS SQS/SNS
    "sqs_receive": re.compile(r"sqs\.receive_message\(|ReceiveMessageCommand"),
    "sns_subscribe": re.compile(r"sns\.subscribe\(|SubscribeCommand"),
    # Azure Service Bus
    "servicebus_receive": re.compile(r"ServiceBusReceiver\(|receive_messages\("),
}

# Blockchain / Smart contract detection patterns
BLOCKCHAIN_PATTERNS = {
    # Solidity (Ethereum)
    "solidity_function": re.compile(r"function\s+(\w+)\s*\([^)]*\)\s+(?:public|external)"),
    "solidity_event": re.compile(r"event\s+(\w+)\s*\("),
    "solidity_modifier": re.compile(r"modifier\s+(\w+)\s*\("),
    "solidity_contract": re.compile(r"contract\s+(\w+)"),
    # Rust (Solana)
    "solana_instruction": re.compile(r"#\[program\]|pub\s+fn\s+(\w+)\s*\([^)]*ctx:\s*Context"),
    # Move (Aptos/Sui)
    "move_function": re.compile(r"public\s+entry\s+fun\s+(\w+)"),
}

# Project type file indicators (files that definitively indicate a project type)
PROJECT_TYPE_INDICATORS = {
    "android": ["AndroidManifest.xml", "build.gradle", "settings.gradle.kts"],
    "ios": ["Info.plist", "*.xcodeproj", "*.xcworkspace"],
    "wpf": ["*.xaml", "App.xaml"],
    "qt": ["*.pro", "CMakeLists.txt"],
    "nextjs": ["next.config.js", "next.config.ts"],
    "angular": ["angular.json"],
    "vue": ["vue.config.js", "vite.config.ts"],
    "sql": ["*.sql", "migrations/"],
    "serverless": ["serverless.yml", "template.yaml", "function.json"],
    "celery": ["celeryconfig.py", "celery.py"],
    "blockchain": ["*.sol", "Cargo.toml", "*.move"],
}
