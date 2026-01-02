import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select


class ProjectManager:
    """Gerencia projetos e configurações .claude."""

    def __init__(self, root_path: str):
        """
        Inicializa o gerenciador de projetos.

        Args:
            root_path: Caminho raiz do projeto principal (onde está o orquestrator-agent)
        """
        self.root_path = Path(root_path)
        self.current_project: Optional[Path] = None
        self._claude_config_cache: Optional[Path] = None
        self.root_claude_path = self.root_path / ".claude"

    async def load_project(self, project_path: str) -> Dict[str, Any]:
        """
        Carrega um projeto e verifica configuração .claude.

        Args:
            project_path: Caminho do projeto a ser carregado

        Returns:
            Dicionário com informações do projeto

        Raises:
            ValueError: Se o caminho for inválido
        """
        path = Path(project_path).expanduser().resolve()

        if not path.exists():
            raise ValueError(f"Caminho não existe: {project_path}")

        if not path.is_dir():
            raise ValueError(f"Caminho não é um diretório: {project_path}")

        # Check for .claude folder
        project_claude = path / ".claude"

        # Copy .claude from root if doesn't exist
        if not project_claude.exists() and self.root_claude_path.exists():
            print(f"[ProjectManager] Copying .claude from root to {project_claude}")
            shutil.copytree(
                self.root_claude_path,
                project_claude,
                ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '.git', '*.db')
            )
            has_claude_config = True
            claude_config_path = str(project_claude)
        else:
            has_claude_config = project_claude.exists()
            claude_config_path = str(project_claude) if has_claude_config else str(self.root_claude_path)

        # Initialize project database
        from .database_manager import db_manager

        project_id = await db_manager.initialize_project_database(str(path))

        # Initialize history database if not done yet
        await db_manager.initialize_history_database()

        # Save to project history (global database)
        await self._save_to_history(project_id, path, path.name, has_claude_config)

        self.current_project = path
        self._claude_config_cache = Path(claude_config_path)

        return {
            "id": project_id,
            "path": str(path),
            "name": path.name,
            "has_claude_config": has_claude_config,
            "claude_config_path": claude_config_path,
            "loaded_at": datetime.utcnow().isoformat()
        }

    async def _save_to_history(self, project_id: str, path: Path, name: str, has_claude_config: bool):
        """
        Save project to global history database.

        Args:
            project_id: Unique project identifier
            path: Project path
            name: Project name
            has_claude_config: Whether project has .claude config
        """
        from .database_manager import db_manager
        from .models.project_history import ProjectHistory

        session_factory = db_manager.get_history_session()

        async with session_factory() as session:
            # Check if project already exists
            result = await session.execute(
                select(ProjectHistory).where(ProjectHistory.id == project_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.access_count += 1
                existing.has_claude_config = has_claude_config
                existing.name = name
            else:
                # Create new record
                new_history = ProjectHistory(
                    id=project_id,
                    path=str(path),
                    name=name,
                    has_claude_config=has_claude_config,
                    is_favorite=False,
                    access_count=1
                )
                session.add(new_history)

            await session.commit()

    def get_working_directory(self) -> str:
        """
        Retorna o diretório de trabalho atual.

        Returns:
            Caminho do diretório de trabalho
        """
        if self.current_project:
            return str(self.current_project)
        return str(self.root_path)

    def get_claude_config_path(self) -> Path:
        """
        Retorna o caminho da configuração .claude a ser usada.

        Returns:
            Caminho da pasta .claude
        """
        if self._claude_config_cache:
            return self._claude_config_cache

        if self.current_project:
            project_claude = self.current_project / ".claude"
            if project_claude.exists():
                self._claude_config_cache = project_claude
                return project_claude

        # Fallback para o .claude da raiz
        root_claude = self.root_path / ".claude"
        self._claude_config_cache = root_claude
        return root_claude

    def get_commands_path(self) -> Optional[Path]:
        """
        Retorna o caminho dos comandos .claude/commands.

        Returns:
            Caminho da pasta de comandos ou None se não existir
        """
        claude_path = self.get_claude_config_path()
        commands_path = claude_path / "commands"
        return commands_path if commands_path.exists() else None

    def get_skills_path(self) -> Optional[Path]:
        """
        Retorna o caminho das skills .claude/skills.

        Returns:
            Caminho da pasta de skills ou None se não existir
        """
        claude_path = self.get_claude_config_path()
        skills_path = claude_path / "skills"
        return skills_path if skills_path.exists() else None

    def reset(self):
        """Reseta o gerenciador para o estado inicial."""
        self.current_project = None
        self._claude_config_cache = None

    def get_project_info(self) -> Optional[Dict[str, Any]]:
        """
        Retorna informações do projeto atual.

        Returns:
            Dicionário com informações do projeto ou None se não houver projeto
        """
        if not self.current_project:
            return None

        return {
            "path": str(self.current_project),
            "name": self.current_project.name,
            "working_directory": self.get_working_directory(),
            "claude_config_path": str(self.get_claude_config_path()),
            "has_commands": self.get_commands_path() is not None,
            "has_skills": self.get_skills_path() is not None,
        }


# Instância global do gerenciador (será inicializada nas rotas)
project_manager: Optional[ProjectManager] = None