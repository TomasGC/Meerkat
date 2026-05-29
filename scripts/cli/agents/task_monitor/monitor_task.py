#!/usr/bin/env python3
"""
Generic Task Monitor using Ollama

Monitors background tasks and uses Ollama exclusively for surveillance
and analysis to consume ZERO Claude tokens.

Usage:
    python monitor_task.py --pid 12345 --type test --log output.log
    python monitor_task.py --pattern "gradle.*test" --type build --log build.log
"""

import argparse
import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


class OllamaMonitor:
    """Wrapper for Ollama API calls"""

    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.model = model

    def analyze_log(self, log_content: str, task_type: str, criteria: Dict) -> Dict:
        """
        Ask Ollama to analyze log content and detect status/problems.

        Returns:
            {
                "status": "running" | "success" | "failed" | "error" | "stalled",
                "problem_detected": bool,
                "summary": str,
                "details": {
                    "errors": [...],
                    "warnings": [...],
                    "affected_files": [...],
                    "suggestions": [...]
                }
            }
        """
        prompt = self._build_analysis_prompt(log_content, task_type, criteria)

        try:
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt,
                text=True,
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0:
                # Parse JSON from Ollama response
                output = result.stdout.strip()
                # Extract JSON block
                import re
                json_match = re.search(r'\{.*\}', output, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))

            # Fallback
            return self._fallback_analysis(log_content, task_type)

        except Exception as e:
            print(f"Ollama error: {e}", file=sys.stderr)
            return self._fallback_analysis(log_content, task_type)

    def _build_analysis_prompt(self, log_content: str, task_type: str, criteria: Dict) -> str:
        """Build prompt for Ollama based on task type"""

        base_prompt = f"""Analyze this {task_type} log and detect status/problems.

Detection criteria:
"""
        for key, value in criteria.items():
            base_prompt += f"- {key}: {value}\n"

        base_prompt += f"""
Log content (last 500 lines):
{log_content[-10000:]}  # Last ~10KB

Respond in JSON:
{{
    "status": "running" | "success" | "failed" | "error" | "stalled",
    "problem_detected": true/false,
    "summary": "brief description",
    "details": {{
        "errors": ["error messages"],
        "warnings": ["warnings"],
        "affected_files": ["file paths"],
        "suggestions": ["recommendations"]
    }}
}}
"""
        return base_prompt

    def _fallback_analysis(self, log_content: str, task_type: str) -> Dict:
        """Fallback regex-based analysis if Ollama fails"""
        import re

        status = "running"
        problem_detected = False
        errors = []
        warnings = []

        # Common error patterns
        error_patterns = [
            r"(?i)error:",
            r"(?i)exception:",
            r"(?i)failed:",
            r"BUILD FAILED",
            r"FAILURE",
        ]

        for pattern in error_patterns:
            matches = re.findall(f"{pattern}.*", log_content, re.IGNORECASE)
            if matches:
                problem_detected = True
                errors.extend(matches[:5])  # First 5 errors

        # Success patterns
        if "BUILD SUCCESSFUL" in log_content:
            status = "success"
        elif problem_detected:
            status = "failed"

        return {
            "status": status,
            "problem_detected": problem_detected,
            "summary": f"Detected {len(errors)} errors" if errors else "Running",
            "details": {
                "errors": errors,
                "warnings": warnings,
                "affected_files": [],
                "suggestions": []
            }
        }


class TaskMonitor:
    """Main task monitoring orchestrator"""

    def __init__(
        self,
        pid: Optional[int] = None,
        pattern: Optional[str] = None,
        log_file: Path = None,
        task_type: str = "generic",
        output_file: Path = Path("task_notification.txt"),
        poll_interval: int = 10,
        stall_threshold: int = 120
    ):
        self.pid = pid
        self.pattern = pattern
        self.log_file = log_file
        self.task_type = task_type
        self.output_file = output_file
        self.poll_interval = poll_interval
        self.stall_threshold = stall_threshold

        self.ollama = OllamaMonitor()
        self.last_log_size = 0
        self.last_log_change = time.time()
        self.start_time = time.time()

    def monitor(self):
        """
        Main monitoring loop - runs until task completes or problem detected.
        """
        print(f"🔍 Monitoring task (type: {self.task_type})")
        print(f"   PID: {self.pid or 'pattern-based'}")
        print(f"   Log: {self.log_file}")
        print(f"   Started: {datetime.now().strftime('%H:%M:%S')}")

        try:
            while True:
                # Check if process still running
                if not self._is_process_running():
                    print("\n✓ Process completed")
                    self._handle_completion()
                    break

                # Read current log
                log_content = self._read_log()

                # Check for stall (log not changing)
                if self._is_stalled(log_content):
                    print("\n⚠️  Task appears stalled!")
                    self._handle_stall(log_content)
                    break

                # Ask Ollama to analyze
                analysis = self.ollama.analyze_log(
                    log_content,
                    self.task_type,
                    self._get_detection_criteria()
                )

                # Problem detected?
                if analysis["problem_detected"]:
                    print(f"\n❌ Problem detected: {analysis['summary']}")
                    self._write_notification(analysis, "PROBLEM")
                    break

                # Still running, wait and poll again
                print(".", end="", flush=True)
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n⚠️  Monitoring interrupted by user")
            self._write_notification(
                {"status": "interrupted", "summary": "User cancelled monitoring"},
                "INTERRUPTED"
            )
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
            self._write_notification(
                {"status": "error", "summary": str(e)},
                "ERROR"
            )

    def _is_process_running(self) -> bool:
        """Check if monitored process is still running"""
        if self.pid:
            try:
                # Check if PID exists
                import psutil
                return psutil.pid_exists(self.pid)
            except ImportError:
                # Fallback: use ps command
                result = subprocess.run(
                    ["ps", "-p", str(self.pid)],
                    capture_output=True
                )
                return result.returncode == 0

        # Pattern-based: check if any process matches
        result = subprocess.run(
            ["pgrep", "-f", self.pattern],
            capture_output=True
        )
        return result.returncode == 0

    def _read_log(self) -> str:
        """Read current log file content"""
        if not self.log_file or not self.log_file.exists():
            return ""

        try:
            with open(self.log_file, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def _is_stalled(self, log_content: str) -> bool:
        """Check if log hasn't changed for too long"""
        current_size = len(log_content)

        if current_size != self.last_log_size:
            # Log changed, reset timer
            self.last_log_size = current_size
            self.last_log_change = time.time()
            return False

        # Check if stalled
        elapsed = time.time() - self.last_log_change
        return elapsed > self.stall_threshold

    def _get_detection_criteria(self) -> Dict:
        """Get detection criteria based on task type"""
        criteria_map = {
            "test": {
                "stall": "No log updates for 60s",
                "failure": "FAILED or Exception in output",
                "success": "BUILD SUCCESSFUL"
            },
            "build": {
                "stall": "No output for 120s",
                "failure": "BUILD FAILED or compilation error",
                "success": "BUILD SUCCESSFUL"
            },
            "deploy": {
                "stall": "No progress for 180s",
                "failure": "Error or deployment failed",
                "success": "Deployment complete"
            }
        }
        return criteria_map.get(self.task_type, {})

    def _handle_completion(self):
        """Handle task completion - final analysis"""
        log_content = self._read_log()
        analysis = self.ollama.analyze_log(
            log_content,
            self.task_type,
            self._get_detection_criteria()
        )
        self._write_notification(analysis, "COMPLETED")

    def _handle_stall(self, log_content: str):
        """Handle stalled task"""
        analysis = self.ollama.analyze_log(
            log_content,
            self.task_type,
            {"stall_detected": True}
        )
        analysis["status"] = "stalled"
        self._write_notification(analysis, "STALLED")

    def _write_notification(self, analysis: Dict, event: str):
        """Write notification file for caller"""
        duration = time.time() - self.start_time

        status_emoji = {
            "success": "✅",
            "failed": "❌",
            "error": "⚠️",
            "stalled": "⏸️",
            "interrupted": "🛑"
        }

        emoji = status_emoji.get(analysis["status"], "❓")

        content = f"""
{emoji} Task Monitor Notification
================================

Event: {event}
Task Type: {self.task_type}
Status: {analysis["status"].upper()}
Duration: {duration:.1f}s

Summary: {analysis.get("summary", "No summary")}

"""

        # Add details if present
        if "details" in analysis:
            details = analysis["details"]

            if details.get("errors"):
                content += "Errors:\n"
                for error in details["errors"][:5]:  # First 5
                    content += f"  - {error}\n"
                content += "\n"

            if details.get("warnings"):
                content += "Warnings:\n"
                for warning in details["warnings"][:3]:
                    content += f"  - {warning}\n"
                content += "\n"

            if details.get("affected_files"):
                content += "Affected Files:\n"
                for file in details["affected_files"]:
                    content += f"  - {file}\n"
                content += "\n"

            if details.get("suggestions"):
                content += "Suggestions:\n"
                for suggestion in details["suggestions"]:
                    content += f"  - {suggestion}\n"
                content += "\n"

        content += f"""
Log File: {self.log_file}
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
================================
"""

        self.output_file.write_text(content, encoding="utf-8")
        print(f"\n📄 Notification written to: {self.output_file.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor background tasks using Ollama (zero Claude tokens)"
    )
    parser.add_argument("--pid", type=int, help="Process ID to monitor")
    parser.add_argument("--pattern", type=str, help="Process name pattern (regex)")
    parser.add_argument("--log", type=Path, required=True, help="Log file to watch")
    parser.add_argument("--type", type=str, default="generic",
                       choices=["test", "build", "deploy", "generic"],
                       help="Task type for detection criteria")
    parser.add_argument("--output", type=Path, default=Path("task_notification.txt"),
                       help="Notification output file")
    parser.add_argument("--interval", type=int, default=10,
                       help="Polling interval in seconds")
    parser.add_argument("--stall-threshold", type=int, default=120,
                       help="Stall threshold in seconds")

    args = parser.parse_args()

    if not args.pid and not args.pattern:
        parser.error("Either --pid or --pattern must be specified")

    monitor = TaskMonitor(
        pid=args.pid,
        pattern=args.pattern,
        log_file=args.log,
        task_type=args.type,
        output_file=args.output,
        poll_interval=args.interval,
        stall_threshold=args.stall_threshold
    )

    monitor.monitor()


if __name__ == "__main__":
    main()
