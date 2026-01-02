import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.project_manager import ProjectManager


class TestProjectManager:
    """Testes unitários para o ProjectManager."""

    def setup_method(self):
        """Setup para cada teste."""
        # Criar diretórios temporários
        self.temp_root = tempfile.mkdtemp()
        self.temp_project = tempfile.mkdtemp()

        # Criar estrutura de pastas .claude no root
        self.root_claude = Path(self.temp_root) / ".claude"
        self.root_claude.mkdir(parents=True)
        (self.root_claude / "commands").mkdir()
        (self.root_claude / "skills").mkdir()

    def teardown_method(self):
        """Cleanup após cada teste."""
        import shutil
        shutil.rmtree(self.temp_root, ignore_errors=True)
        shutil.rmtree(self.temp_project, ignore_errors=True)

    def test_load_valid_project(self):
        """Teste de carregamento de projeto válido."""
        manager = ProjectManager(self.temp_root)

        result = manager.load_project(self.temp_project)

        assert result["path"] == str(Path(self.temp_project).resolve())
        assert result["name"] == Path(self.temp_project).name
        assert result["has_claude_config"] == False
        assert "loaded_at" in result
        assert manager.current_project == Path(self.temp_project).resolve()

    def test_project_without_claude_uses_root(self):
        """Teste de projeto sem pasta .claude (deve usar root)."""
        manager = ProjectManager(self.temp_root)

        # Projeto sem .claude
        result = manager.load_project(self.temp_project)

        assert result["has_claude_config"] == False
        assert result["claude_config_path"] == str(self.root_claude)

        # Deve usar configuração do root
        config_path = manager.get_claude_config_path()
        assert config_path == self.root_claude

    def test_project_with_claude(self):
        """Teste de projeto com sua própria pasta .claude."""
        # Criar .claude no projeto
        project_claude = Path(self.temp_project) / ".claude"
        project_claude.mkdir()

        manager = ProjectManager(self.temp_root)
        result = manager.load_project(self.temp_project)

        assert result["has_claude_config"] == True
        assert Path(result["claude_config_path"]).resolve() == project_claude.resolve()

        # Deve usar configuração do projeto
        config_path = manager.get_claude_config_path()
        assert config_path.resolve() == project_claude.resolve()

    def test_invalid_project_path(self):
        """Teste de projeto inválido/inexistente."""
        manager = ProjectManager(self.temp_root)

        # Caminho inexistente
        with pytest.raises(ValueError, match="Caminho não existe"):
            manager.load_project("/caminho/inexistente")

        # Caminho que é arquivo, não diretório
        temp_file = Path(self.temp_root) / "arquivo.txt"
        temp_file.write_text("test")

        with pytest.raises(ValueError, match="não é um diretório"):
            manager.load_project(str(temp_file))

    def test_get_working_directory(self):
        """Teste de obtenção do diretório de trabalho."""
        manager = ProjectManager(self.temp_root)

        # Sem projeto carregado, deve retornar root
        assert manager.get_working_directory() == str(self.temp_root)

        # Com projeto carregado
        manager.load_project(self.temp_project)
        assert manager.get_working_directory() == str(Path(self.temp_project).resolve())

    def test_reset_manager(self):
        """Teste de reset do gerenciador."""
        manager = ProjectManager(self.temp_root)
        manager.load_project(self.temp_project)

        assert manager.current_project is not None

        manager.reset()

        assert manager.current_project is None
        assert manager.get_working_directory() == str(self.temp_root)

    def test_get_commands_and_skills_paths(self):
        """Teste de obtenção de caminhos de comandos e skills."""
        manager = ProjectManager(self.temp_root)

        # Com comandos e skills existentes
        assert manager.get_commands_path() == self.root_claude / "commands"
        assert manager.get_skills_path() == self.root_claude / "skills"

        # Remover pastas de comandos e skills
        import shutil
        shutil.rmtree(self.root_claude / "commands")
        shutil.rmtree(self.root_claude / "skills")

        # Sem comandos e skills
        assert manager.get_commands_path() is None
        assert manager.get_skills_path() is None

    def test_project_info(self):
        """Teste de informações do projeto."""
        manager = ProjectManager(self.temp_root)

        # Sem projeto carregado
        assert manager.get_project_info() is None

        # Com projeto carregado
        manager.load_project(self.temp_project)
        info = manager.get_project_info()

        assert info is not None
        assert info["path"] == str(Path(self.temp_project).resolve())
        assert info["name"] == Path(self.temp_project).name
        assert info["working_directory"] == str(Path(self.temp_project).resolve())
        assert info["has_commands"] == True  # Root tem commands
        assert info["has_skills"] == True    # Root tem skills