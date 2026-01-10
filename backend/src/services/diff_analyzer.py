"""Diff analyzer service for capturing git changes."""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional

from ..schemas.card import DiffStats, FileDiff


class DiffAnalyzer:
    """Service for analyzing git diffs in worktrees."""

    async def capture_diff(self, worktree_path: str, branch_name: str) -> Optional[DiffStats]:
        """
        Capture diff statistics from a worktree.

        Args:
            worktree_path: Path to the worktree
            branch_name: Name of the branch

        Returns:
            DiffStats object with captured statistics or None if capture fails
        """
        if not os.path.exists(worktree_path):
            return None

        try:
            # Get the base branch (usually main or master)
            base_branch = await self._get_base_branch(worktree_path)

            # Get file status changes
            files_data = await self._get_file_changes(worktree_path, base_branch)

            # Get line changes statistics
            lines_data = await self._get_line_changes(worktree_path, base_branch)

            # Get detailed diff content for each file
            file_diffs = await self._get_all_file_diffs(worktree_path, base_branch, files_data)

            # Combine all data
            diff_stats = DiffStats(
                files_added=files_data["added"],
                files_modified=files_data["modified"],
                files_removed=files_data["removed"],
                lines_added=lines_data["added"],
                lines_removed=lines_data["removed"],
                total_changes=lines_data["added"] + lines_data["removed"],
                captured_at=datetime.utcnow().isoformat(),
                branch_name=branch_name,
                file_diffs=file_diffs
            )

            return diff_stats

        except Exception as e:
            print(f"Error capturing diff: {e}")
            return None

    async def _get_base_branch(self, worktree_path: str) -> str:
        """Get the base branch name (main or master)."""
        try:
            # Try to find main branch
            process = await asyncio.create_subprocess_exec(
                "git", "-C", worktree_path, "rev-parse", "--verify", "main",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            if process.returncode == 0:
                return "main"

            # Fallback to master
            return "master"

        except Exception:
            return "main"

    async def _get_file_changes(self, worktree_path: str, base_branch: str) -> Dict[str, List[str]]:
        """
        Get files added, modified, and removed.

        Returns:
            Dict with keys: added, modified, removed
        """
        try:
            # Run git diff --name-status
            process = await asyncio.create_subprocess_exec(
                "git", "-C", worktree_path, "diff", "--name-status", f"{base_branch}...HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return {"added": [], "modified": [], "removed": []}

            output = stdout.decode("utf-8").strip()
            if not output:
                return {"added": [], "modified": [], "removed": []}

            added = []
            modified = []
            removed = []

            for line in output.split("\n"):
                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue

                status = parts[0]
                filepath = parts[1]

                if status.startswith("A"):
                    added.append(filepath)
                elif status.startswith("M"):
                    modified.append(filepath)
                elif status.startswith("D"):
                    removed.append(filepath)
                elif status.startswith("R"):
                    # Renamed files - treat as modified
                    modified.append(filepath)

            return {
                "added": added,
                "modified": modified,
                "removed": removed
            }

        except Exception as e:
            print(f"Error getting file changes: {e}")
            return {"added": [], "modified": [], "removed": []}

    async def _get_line_changes(self, worktree_path: str, base_branch: str) -> Dict[str, int]:
        """
        Get lines added and removed.

        Returns:
            Dict with keys: added, removed
        """
        try:
            # Run git diff --shortstat
            process = await asyncio.create_subprocess_exec(
                "git", "-C", worktree_path, "diff", "--shortstat", f"{base_branch}...HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return {"added": 0, "removed": 0}

            output = stdout.decode("utf-8").strip()
            if not output:
                return {"added": 0, "removed": 0}

            # Parse output like: "3 files changed, 45 insertions(+), 12 deletions(-)"
            lines_added = 0
            lines_removed = 0

            if "insertion" in output:
                # Extract number before "insertion"
                parts = output.split("insertion")
                if parts:
                    num_str = parts[0].strip().split()[-1]
                    try:
                        lines_added = int(num_str)
                    except ValueError:
                        pass

            if "deletion" in output:
                # Extract number before "deletion"
                parts = output.split("deletion")
                if parts:
                    num_str = parts[0].strip().split()[-1]
                    try:
                        lines_removed = int(num_str)
                    except ValueError:
                        pass

            return {
                "added": lines_added,
                "removed": lines_removed
            }

        except Exception as e:
            print(f"Error getting line changes: {e}")
            return {"added": 0, "removed": 0}

    async def _get_all_file_diffs(
        self, worktree_path: str, base_branch: str, files_data: Dict[str, List[str]]
    ) -> List[FileDiff]:
        """
        Get diff content for all changed files.

        Args:
            worktree_path: Path to the worktree
            base_branch: Base branch to compare against
            files_data: Dict with added, modified, removed file lists

        Returns:
            List of FileDiff objects with diff content
        """
        file_diffs = []

        # Get full diff output
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "-C", worktree_path, "diff", f"{base_branch}...HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return []

            full_diff = stdout.decode("utf-8", errors="replace")

            # Parse the diff into individual file diffs
            current_file = None
            current_content = []
            current_status = "modified"

            for line in full_diff.split("\n"):
                if line.startswith("diff --git"):
                    # Save previous file if exists
                    if current_file and current_content:
                        file_diffs.append(FileDiff(
                            path=current_file,
                            status=current_status,
                            content="\n".join(current_content)
                        ))

                    # Extract file path from diff line
                    parts = line.split(" b/")
                    if len(parts) >= 2:
                        current_file = parts[-1].strip()
                    else:
                        current_file = None

                    # Determine status
                    if current_file in files_data["added"]:
                        current_status = "added"
                    elif current_file in files_data["removed"]:
                        current_status = "removed"
                    else:
                        current_status = "modified"

                    current_content = [line]
                elif current_file:
                    current_content.append(line)

            # Save last file
            if current_file and current_content:
                file_diffs.append(FileDiff(
                    path=current_file,
                    status=current_status,
                    content="\n".join(current_content)
                ))

        except Exception as e:
            print(f"Error getting all file diffs: {e}")

        return file_diffs

    async def get_detailed_diff(self, worktree_path: str, file_path: str) -> Optional[str]:
        """
        Get detailed diff for a specific file.

        Args:
            worktree_path: Path to the worktree
            file_path: Relative path to the file

        Returns:
            Diff content as string or None if failed
        """
        if not os.path.exists(worktree_path):
            return None

        try:
            base_branch = await self._get_base_branch(worktree_path)

            # Run git diff for specific file
            process = await asyncio.create_subprocess_exec(
                "git", "-C", worktree_path, "diff", f"{base_branch}...HEAD", "--", file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return None

            return stdout.decode("utf-8")

        except Exception as e:
            print(f"Error getting detailed diff: {e}")
            return None
