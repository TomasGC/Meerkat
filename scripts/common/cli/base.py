#!/usr/bin/env python3
"""
Base class for all CLI scripts.

Provides common functionality:
- Argument parsing with standard arguments (--format)
- Automatic logging and metrics initialization
- Error handling and exit codes
- Output formatting (JSON/text/summary)
"""

from abc import ABC, abstractmethod
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from typing import Any

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.formatters import format_json
from common.logger import get_defaults


class BaseCLIScript(ABC):
    """
    Abstract base class for all CLI scripts.

    Provides:
    - Automatic argparse setup
    - Logging initialization
    - Error handling
    - Output formatting (JSON/text/summary)
    - Exit code handling

    Subclasses must implement:
    - execute() - Main script logic

    Subclasses can override:
    - setup_parser() - Add custom arguments
    - format_text() - Custom text formatting
    - format_summary() - Custom summary formatting
    """

    def __init__(self):
        """Initialize logging and metrics."""
        self.logger, self.metrics = get_defaults(module_name=self.__class__.__module__)

    def setup_parser(self, parser: ArgumentParser) -> None:
        """
        Add script-specific arguments to parser.

        Override this method to add custom arguments.
        Default arguments (--format) are added automatically.

        Args:
            parser: ArgumentParser instance

        Example:
            def setup_parser(self, parser):
                parser.add_argument("--path", type=Path, default=Path("."))
                parser.add_argument("--recursive", action="store_true")
        """
        pass

    @abstractmethod
    def execute(self, args) -> dict[str, Any]:
        """
        Execute script logic.

        Args:
            args: Parsed command-line arguments

        Returns:
            dict: Result dictionary (will be formatted according to --format)

        Raises:
            Exception: Any error during execution

        Example:
            def execute(self, args) -> dict:
                result = do_work(args.path)
                return {"success": True, "result": result}
        """
        pass

    def format_text(self, result: dict) -> str:
        """
        Format result as human-readable text.

        Override this method for custom text formatting.
        Default: pretty-printed JSON.

        Args:
            result: Result dictionary from execute()

        Returns:
            Formatted string

        Example:
            def format_text(self, result) -> str:
                return f"Files: {result['count']}\nSize: {result['size']}"
        """
        return format_json(result)

    def format_summary(self, result: dict) -> str:
        """
        Format result as brief summary.

        Override this method for custom summary formatting.
        Default: Same as format_text().

        Args:
            result: Result dictionary from execute()

        Returns:
            Summary string (should be 1-3 lines)

        Example:
            def format_summary(self, result) -> str:
                return f"Processed {result['count']} files"
        """
        return self.format_text(result)

    def create_parser(self) -> ArgumentParser:
        """
        Create argument parser with common arguments.

        Returns:
            ArgumentParser with default arguments

        Note:
            Automatically calls setup_parser() to allow subclasses to add custom args.
        """
        parser = ArgumentParser(
            description=self.__doc__ or "CLI script",
            formatter_class=RawDescriptionHelpFormatter
        )

        # Common arguments
        parser.add_argument(
            "--format",
            "-f",
            choices=["json", "text", "summary"],
            default="json",
            help="Output format (default: json)"
        )

        # Allow subclass to add custom arguments
        self.setup_parser(parser)

        return parser

    def output(self, result: dict, format: str) -> None:
        """
        Output result in requested format.

        Args:
            result: Result dictionary
            format: Output format (json/text/summary)
        """
        if format == "json":
            print(format_json(result))
        elif format == "text":
            print(self.format_text(result))
        else:  # summary
            print(self.format_summary(result))

    def run(self, args: list[str] | None = None) -> int:
        """
        Main entry point - handles full execution lifecycle.

        - Parses arguments
        - Calls execute()
        - Handles errors
        - Formats output
        - Returns exit code

        Args:
            args: Command-line arguments (None = sys.argv)

        Returns:
            Exit code (0 = success, 1 = error, 130 = interrupted)
        """
        try:
            parser = self.create_parser()
            parsed_args = parser.parse_args(args)

            # Execute script logic
            result = self.execute(parsed_args)

            # Output result
            self.output(result, parsed_args.format)

            # Track success metric
            self.metrics.track(
                f"{self.__class__.__name__}.success",
                {"format": parsed_args.format}
            )

            return 0

        except KeyboardInterrupt:
            self.logger.warning("Interrupted by user")
            return 130

        except Exception as e:
            self.logger.error(f"Error: {e}", exc_info=True)
            self.metrics.track(
                f"{self.__class__.__name__}.error",
                {"error_type": type(e).__name__}
            )
            return 1


def create_cli_script(script_class: type[BaseCLIScript]) -> None:
    """
    Create and run CLI script.

    Usage:
        if __name__ == "__main__":
            create_cli_script(MyScript)

    Args:
        script_class: Subclass of BaseCLIScript
    """
    script = script_class()
    sys.exit(script.run())
