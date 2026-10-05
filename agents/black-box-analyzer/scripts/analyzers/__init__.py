#!/usr/bin/env python3
"""Analyzers package for universal project type analysis.

Each analyzer handles a specific project type:
- APIAnalyzer: REST/GraphQL/gRPC APIs
- CLIAnalyzer: Command-line applications
- MobileAnalyzer: Android/iOS apps
- DesktopAnalyzer: Windows/Mac/Linux desktop apps
- FrontendAnalyzer: React/Vue/Angular
- FullstackAnalyzer: Next.js/Remix/SvelteKit
- LLMAnalyzer: LangChain/CrewAI agents
- SQLAnalyzer: SQL projects (stored procedures, triggers)
- ServerlessAnalyzer: AWS Lambda, Azure Functions, Cloud Functions
- WorkerAnalyzer: Celery, Sidekiq, Bull, asynq
- MessageQueueAnalyzer: Kafka, RabbitMQ, SQS, Service Bus
- SmartContractAnalyzer: Solidity, Rust/Solana, Move
"""

from .api_analyzer import APIAnalyzer
from .base_analyzer import BaseAnalyzer
from .blockchain import SmartContractAnalyzer
from .cli_analyzer import CLIAnalyzer
from .desktop_analyzer import DesktopAnalyzer
from .event_driven import MessageQueueAnalyzer, ServerlessAnalyzer, WorkerAnalyzer
from .frontend_analyzer import FrontendAnalyzer
from .fullstack_analyzer import FullstackAnalyzer
from .llm_analyzer import LLMAnalyzer
from .mobile_analyzer import MobileAnalyzer
from .sql_analyzer import SQLAnalyzer

__all__ = [
    "BaseAnalyzer",
    "APIAnalyzer",
    "CLIAnalyzer",
    "MobileAnalyzer",
    "DesktopAnalyzer",
    "FrontendAnalyzer",
    "FullstackAnalyzer",
    "LLMAnalyzer",
    "SQLAnalyzer",
    "ServerlessAnalyzer",
    "WorkerAnalyzer",
    "MessageQueueAnalyzer",
    "SmartContractAnalyzer",
]
