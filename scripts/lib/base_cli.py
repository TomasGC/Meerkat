#!/usr/bin/env python3
"""
Base class for CLI scripts using template method pattern.

This provides a common structure for all CLI scripts with:
- Argument parsing
- Error handling
- Logging
- JSON output support
"""

import argparse
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseCLIScript(ABC):
    """Abstract base class for CLI scripts."""

    def __init__(self):
        """Initialize the CLI script."""
        self.parser = argparse.ArgumentParser(description=self.__doc__)
        self.args: Optional[argparse.Namespace] = None

    @abstractmethod
    def add_arguments(self) -> None:
        """Add script-specific arguments to the parser."""
        pass

    @abstractmethod
    def execute(self) -> None:
        """Execute the main logic of the script."""
        pass

    def run(self, argv: Optional[list] = None) -> int:
        """
        Run the script with the template method pattern.

        Args:
            argv: Command-line arguments (None = sys.argv)

        Returns:
            Exit code (0 = success, 1 = error)
        """
        try:
            # Parse arguments
            self.add_arguments()
            self.args = self.parser.parse_args(argv)

            # Execute main logic
            self.execute()

            return 0

        except SystemExit as e:
            # Propagate argument parsing errors
            return e.code if isinstance(e.code, int) else 1

        except Exception as e:
            self.error(f"Error: {e}")
            return 1

    def error(self, message: str, exit_code: int = 1) -> None:
        """
        Print error message and exit.

        Args:
            message: Error message
            exit_code: Exit code (default: 1)
        """
        print(f"Error: {message}", file=sys.stderr)
        sys.exit(exit_code)

    def success(self, message: str) -> None:
        """Print success message."""
        print(message)


def main_template(script_class: type) -> None:
    """
    Template for script entry points.

    Usage:
        if __name__ == "__main__":
            main_template(MyScriptClass)
    """
    script = script_class()
    sys.exit(script.run())
