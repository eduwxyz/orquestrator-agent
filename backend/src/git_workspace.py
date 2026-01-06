"""Git Workspace Manager for card isolation using worktrees."""

import asyncio
import time
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

# Limite de worktrees simultaneos
MAX_CONCURRENT_WORKTREES = 10


@dataclass
class WorktreeResult:
    """Result of worktree creation operation."""
    success: bool
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    error: Optional[str] = None


class GitWorkspaceManager:
    """Gerenciador de worktrees do Git para isolamento de cards."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.worktrees_dir = self.project_path / ".worktrees"

    async def _run_git_command(
        self,
        args: List[str],
        cwd: Optional[str] = None
    ) -> tuple[int, str, str]:
        """
        Executa comando git de forma segura.

        Args:
            args: Lista de argumentos (ex: ["git", "worktree", "add", ...])
            cwd: Diretorio de trabalho (usa project_path se nao especificado)

        Returns:
            Tupla (returncode, stdout, stderr)
        """
        work_dir = cwd or str(self.project_path)

        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode(), stderr.decode()

    async def _get_default_branch(self) -> str:
        """Detecta branch principal do repositorio."""
        # Tentar via remote HEAD
        returncode, stdout, _ = await self._run_git_command(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"]
        )
        if returncode == 0 and stdout.strip():
            return stdout.strip().replace("refs/remotes/origin/", "")

        # Tentar via config
        returncode, stdout, _ = await self._run_git_command(
            ["git", "config", "--get", "init.defaultBranch"]
        )
        if returncode == 0 and stdout.strip():
            return stdout.strip()

        # Verificar se main ou master existe
        for branch in ["main", "master"]:
            returncode, _, _ = await self._run_git_command(
                ["git", "rev-parse", "--verify", branch]
            )
            if returncode == 0:
                return branch

        return "main"  # Fallback

    async def recover_state(self) -> None:
        """
        Recupera de estado inconsistente do git.
        Deve ser chamado na inicializacao do manager.
        """
        # Verificar se ha merge em andamento
        merge_head = self.project_path / ".git" / "MERGE_HEAD"
        if merge_head.exists():
            await self._run_git_command(["git", "merge", "--abort"])

        # Verificar se ha rebase em andamento
        rebase_dir = self.project_path / ".git" / "rebase-merge"
        if rebase_dir.exists():
            await self._run_git_command(["git", "rebase", "--abort"])

    async def _branch_exists(self, branch_name: str) -> bool:
        """Verifica se branch existe."""
        returncode, stdout, _ = await self._run_git_command(
            ["git", "branch", "--list", branch_name]
        )
        return returncode == 0 and stdout.strip() != ""

    async def _cleanup_stale_branch(self, branch_name: str) -> None:
        """Remove branch orfa se existir."""
        if await self._branch_exists(branch_name):
            await self._run_git_command(["git", "branch", "-D", branch_name])

    async def create_worktree(
        self,
        card_id: str,
        base_branch: Optional[str] = None
    ) -> WorktreeResult:
        """
        Cria worktree isolado para um card.

        Args:
            card_id: ID do card
            base_branch: Branch base (detecta automaticamente se nao especificado)

        Returns:
            WorktreeResult com path e nome da branch
        """
        # Verificar limite de worktrees
        active = await self.list_active_worktrees()
        card_worktrees = [w for w in active if w.get('branch', '').startswith('agent/')]
        if len(card_worktrees) >= MAX_CONCURRENT_WORKTREES:
            return WorktreeResult(
                success=False,
                error=f"Limite de {MAX_CONCURRENT_WORKTREES} worktrees atingido"
            )

        # Criar diretorio de worktrees se nao existir
        self.worktrees_dir.mkdir(exist_ok=True)

        # Detectar branch base
        if not base_branch:
            base_branch = await self._get_default_branch()

        # Definir paths com prefixo mais seguro
        short_id = card_id[:8] if len(card_id) > 8 else card_id
        timestamp = int(time.time())
        branch_name = f"agent/{short_id}-{timestamp}"
        worktree_path = self.worktrees_dir / f"card-{short_id}"

        # Verificar se worktree ja existe
        if worktree_path.exists():
            # Tentar limpar worktree antigo
            await self._run_git_command(
                ["git", "worktree", "remove", str(worktree_path), "--force"]
            )

        # Limpar branch orfa se existir
        await self._cleanup_stale_branch(branch_name)

        # Criar worktree com nova branch baseada na branch principal
        returncode, stdout, stderr = await self._run_git_command([
            "git", "worktree", "add",
            str(worktree_path),
            "-b", branch_name,
            base_branch
        ])

        if returncode != 0:
            return WorktreeResult(
                success=False,
                error=f"Failed to create worktree: {stderr}"
            )

        return WorktreeResult(
            success=True,
            worktree_path=str(worktree_path),
            branch_name=branch_name
        )

    async def cleanup_worktree(
        self,
        card_id: str,
        branch_name: str,
        delete_branch: bool = True
    ) -> bool:
        """
        Remove worktree e opcionalmente a branch.

        Args:
            card_id: ID do card
            branch_name: Nome da branch
            delete_branch: Se deve deletar a branch tambem

        Returns:
            True se cleanup bem-sucedido
        """
        short_id = card_id[:8] if len(card_id) > 8 else card_id
        worktree_path = self.worktrees_dir / f"card-{short_id}"

        # Remover worktree
        if worktree_path.exists():
            returncode, _, stderr = await self._run_git_command(
                ["git", "worktree", "remove", str(worktree_path), "--force"]
            )
            if returncode != 0:
                print(f"Warning: Failed to remove worktree: {stderr}")
                return False

        # Deletar branch se solicitado
        if delete_branch and branch_name:
            returncode, _, stderr = await self._run_git_command(
                ["git", "branch", "-D", branch_name]
            )
            if returncode != 0:
                print(f"Warning: Failed to delete branch: {stderr}")

        return True

    async def list_active_worktrees(self) -> List[Dict[str, str]]:
        """Lista todos os worktrees ativos."""
        _, output, _ = await self._run_git_command(
            ["git", "worktree", "list", "--porcelain"]
        )

        worktrees = []
        current = {}

        for line in output.split('\n'):
            if line.startswith('worktree '):
                if current:
                    worktrees.append(current)
                current = {'path': line.split(' ', 1)[1]}
            elif line.startswith('branch '):
                current['branch'] = line.split(' ', 1)[1].replace('refs/heads/', '')

        if current:
            worktrees.append(current)

        return worktrees

    async def cleanup_orphan_worktrees(self, active_card_ids: List[str]) -> int:
        """
        Remove worktrees orfaos (sem card associado).

        Args:
            active_card_ids: Lista de IDs de cards ativos

        Returns:
            Numero de worktrees removidos
        """
        removed = 0
        worktrees = await self.list_active_worktrees()

        for wt in worktrees:
            branch = wt.get('branch', '')
            if branch.startswith('agent/'):
                # Extrair card_id do branch name (agent/{short_id}-{timestamp})
                parts = branch.replace('agent/', '').split('-')
                if parts:
                    short_id = parts[0]
                    # Verificar se algum card ativo tem esse short_id
                    is_active = any(
                        card_id.startswith(short_id)
                        for card_id in active_card_ids
                    )
                    if not is_active:
                        # Worktree orfao - remover
                        await self._run_git_command(
                            ["git", "worktree", "remove", wt['path'], "--force"]
                        )
                        await self._run_git_command(
                            ["git", "branch", "-D", branch]
                        )
                        removed += 1

        return removed

    async def list_all_branches(self) -> List[Dict[str, str]]:
        """Lista todas as branches locais e remotas do repositório."""

        # Listar branches locais
        returncode, stdout, _ = await self._run_git_command(
            ["git", "branch", "--format=%(refname:short)"]
        )

        local_branches = []
        if returncode == 0:
            for branch in stdout.strip().split('\n'):
                if branch and not branch.startswith('agent/'):
                    local_branches.append({
                        "name": branch,
                        "type": "local"
                    })

        # Listar branches remotas principais (ignorar agent/*)
        returncode, stdout, _ = await self._run_git_command(
            ["git", "branch", "-r", "--format=%(refname:short)"]
        )

        remote_branches = []
        if returncode == 0:
            for branch in stdout.strip().split('\n'):
                if branch and not branch.startswith('origin/agent/'):
                    # Remover prefixo origin/
                    clean_name = branch.replace('origin/', '')
                    if clean_name not in ['HEAD', 'main', 'master'] and \
                       not any(b['name'] == clean_name for b in local_branches):
                        remote_branches.append({
                            "name": clean_name,
                            "type": "remote"
                        })

        return local_branches + remote_branches

    def is_git_repo(self) -> bool:
        """Verifica se o projeto eh um repositorio git."""
        git_dir = self.project_path / ".git"
        return git_dir.exists()
