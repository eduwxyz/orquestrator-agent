"""Service to check Claude Code usage limits."""

import asyncio
import logging
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UsageInfo:
    """Claude Code usage information."""
    session_used_percent: float
    daily_used_percent: float
    is_safe_to_execute: bool
    raw_output: str
    error: Optional[str] = None


class UsageCheckerService:
    """Service to check Claude Code API usage limits."""

    def __init__(self, limit_threshold: int = 80):
        """
        Initialize the usage checker.

        Args:
            limit_threshold: Percentage threshold above which execution should pause
        """
        self.limit_threshold = limit_threshold

    async def check_usage(self) -> UsageInfo:
        """
        Check current Claude Code usage by running `claude /usage`.

        Returns:
            UsageInfo with usage percentages and safety status
        """
        try:
            # Run claude /usage command
            process = await asyncio.create_subprocess_exec(
                "claude",
                "/usage",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0
            )

            output = stdout.decode("utf-8")
            error_output = stderr.decode("utf-8")

            if process.returncode != 0:
                logger.error(f"claude /usage failed: {error_output}")
                return UsageInfo(
                    session_used_percent=0,
                    daily_used_percent=0,
                    is_safe_to_execute=False,
                    raw_output=error_output,
                    error=f"Command failed with code {process.returncode}"
                )

            # Parse the output
            return self._parse_usage_output(output)

        except asyncio.TimeoutError:
            logger.error("claude /usage timed out")
            return UsageInfo(
                session_used_percent=0,
                daily_used_percent=0,
                is_safe_to_execute=False,
                raw_output="",
                error="Command timed out"
            )
        except FileNotFoundError:
            logger.error("claude command not found")
            return UsageInfo(
                session_used_percent=0,
                daily_used_percent=0,
                is_safe_to_execute=True,  # Assume safe if we can't check
                raw_output="",
                error="claude command not found"
            )
        except Exception as e:
            logger.error(f"Error checking usage: {e}")
            return UsageInfo(
                session_used_percent=0,
                daily_used_percent=0,
                is_safe_to_execute=True,  # Assume safe on error
                raw_output="",
                error=str(e)
            )

    def _parse_usage_output(self, output: str) -> UsageInfo:
        """
        Parse the output of `claude /usage`.

        Expected format includes lines like:
        - "Session: 45% used"
        - "Daily: 23% used"
        Or similar percentage indicators.
        """
        session_percent = 0.0
        daily_percent = 0.0

        # Try to find percentage patterns
        # Pattern: number followed by % (with optional spaces)
        percent_pattern = r'(\d+(?:\.\d+)?)\s*%'

        lines = output.lower().split('\n')
        for line in lines:
            matches = re.findall(percent_pattern, line)
            if matches:
                value = float(matches[0])
                if 'session' in line:
                    session_percent = value
                elif 'daily' in line or 'day' in line:
                    daily_percent = value
                elif 'limit' in line or 'used' in line:
                    # Generic usage line, use as session if not set
                    if session_percent == 0:
                        session_percent = value

        # Determine if safe to execute
        max_usage = max(session_percent, daily_percent)
        is_safe = max_usage < self.limit_threshold

        logger.info(
            f"[UsageChecker] Session: {session_percent}%, Daily: {daily_percent}%, "
            f"Safe: {is_safe} (threshold: {self.limit_threshold}%)"
        )

        return UsageInfo(
            session_used_percent=session_percent,
            daily_used_percent=daily_percent,
            is_safe_to_execute=is_safe,
            raw_output=output,
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the usage checker."""
        return {
            "limit_threshold": self.limit_threshold,
            "description": f"Pauses execution when usage > {self.limit_threshold}%"
        }


def get_usage_checker_service(limit_threshold: int = 80) -> UsageCheckerService:
    """Get usage checker service instance."""
    return UsageCheckerService(limit_threshold=limit_threshold)
