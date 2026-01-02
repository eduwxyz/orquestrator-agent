from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.project import ActiveProject
from src.project_manager import ProjectManager, project_manager as global_project_manager


# Esquemas Pydantic
class LoadProjectRequest(BaseModel):
    """Requisição para carregar um projeto."""
    path: str


class LoadProjectResponse(BaseModel):
    """Resposta ao carregar um projeto."""
    success: bool
    project: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CurrentProjectResponse(BaseModel):
    """Resposta com o projeto atual."""
    success: bool
    project: Optional[Dict[str, Any]] = None


# Router da API
router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_manager() -> ProjectManager:
    """
    Obtém ou cria a instância do gerenciador de projetos.

    Returns:
        Instância do ProjectManager
    """
    global global_project_manager

    if global_project_manager is None:
        # Inicializa com o diretório raiz do projeto
        # (3 níveis acima: routes -> src -> backend -> raiz)
        root_path = Path(__file__).parent.parent.parent.parent
        global_project_manager = ProjectManager(str(root_path))

    return global_project_manager


@router.post("/load", response_model=LoadProjectResponse)
async def load_project(request: LoadProjectRequest):
    """
    Carrega um novo projeto.

    Args:
        request: Dados da requisição com o caminho do projeto

    Returns:
        Informações do projeto carregado

    Raises:
        HTTPException: Se houver erro ao carregar o projeto
    """
    try:
        # Obtém o gerenciador
        manager = get_project_manager()

        # Carrega o projeto (now async)
        project_info = await manager.load_project(request.path)

        # Salvar no banco de dados
        async with async_session_maker() as session:
            # Limpar projetos anteriores
            await session.execute(delete(ActiveProject))

            # Salvar novo projeto ativo
            active_project = ActiveProject(
                id=project_info["id"],
                path=project_info["path"],
                name=project_info["name"],
                has_claude_config=project_info["has_claude_config"],
                claude_config_path=project_info["claude_config_path"],
            )
            session.add(active_project)
            await session.commit()

        return LoadProjectResponse(
            success=True,
            project=project_info
        )

    except ValueError as e:
        # Erro de validação (caminho inválido, etc)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Erro genérico
        print(f"[ProjectsRoute] Error loading project: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao carregar projeto: {str(e)}")


@router.get("/current", response_model=CurrentProjectResponse)
async def get_current_project():
    """
    Retorna o projeto atualmente carregado.

    Returns:
        Informações do projeto atual ou None se não houver
    """
    try:
        async with async_session_maker() as session:
            # Busca o projeto ativo mais recente
            result = await session.execute(
                select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
            )
            project = result.scalar_one_or_none()

            if project:
                # Recarrega no gerenciador se necessário
                manager = get_project_manager()
                if not manager.current_project or str(manager.current_project) != project.path:
                    try:
                        manager.load_project(project.path)
                    except Exception as e:
                        print(f"[ProjectsRoute] Failed to reload project: {e}")

                return CurrentProjectResponse(
                    success=True,
                    project=project.to_dict()
                )

        return CurrentProjectResponse(
            success=True,
            project=None
        )

    except Exception as e:
        print(f"[ProjectsRoute] Error getting current project: {e}")
        return CurrentProjectResponse(
            success=False,
            project=None
        )


@router.delete("/current")
async def clear_current_project():
    """
    Remove o projeto atual (volta para o padrão).

    Returns:
        Status da operação
    """
    try:
        # Limpa do banco
        async with async_session_maker() as session:
            await session.execute(delete(ActiveProject))
            await session.commit()

        # Limpa do gerenciador
        manager = get_project_manager()
        manager.reset()

        return {"success": True, "message": "Projeto removido com sucesso"}

    except Exception as e:
        print(f"[ProjectsRoute] Error clearing project: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar projeto: {str(e)}")


@router.get("/info")
async def get_project_info():
    """
    Retorna informações detalhadas do projeto atual.

    Returns:
        Informações detalhadas do projeto
    """
    try:
        manager = get_project_manager()
        info = manager.get_project_info()

        if not info:
            return {
                "success": True,
                "message": "Nenhum projeto carregado",
                "info": None
            }

        return {
            "success": True,
            "info": info
        }

    except Exception as e:
        print(f"[ProjectsRoute] Error getting project info: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter informações: {str(e)}")


@router.get("/recent")
async def get_recent_projects(
    limit: int = 10,
    filter_type: str = "recent"  # recent or favorites
):
    """
    Get recent or favorite projects.

    Args:
        limit: Maximum number of projects to return
        filter_type: Filter by 'recent' or 'favorites'

    Returns:
        List of projects
    """
    try:
        from src.database_manager import db_manager
        from src.models.project_history import ProjectHistory

        # Initialize history database if needed
        await db_manager.initialize_history_database()

        session_factory = db_manager.get_history_session()

        async with session_factory() as session:
            query = select(ProjectHistory)

            if filter_type == "favorites":
                query = query.where(ProjectHistory.is_favorite == True)

            query = query.order_by(ProjectHistory.last_accessed.desc()).limit(limit)
            result = await session.execute(query)
            projects = result.scalars().all()

            return {
                "success": True,
                "projects": [p.to_dict() for p in projects]
            }

    except Exception as e:
        print(f"[ProjectsRoute] Error getting recent projects: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter projetos recentes: {str(e)}")


@router.post("/{project_id}/favorite")
async def toggle_favorite(project_id: str):
    """
    Toggle favorite status of a project.

    Args:
        project_id: ID of the project

    Returns:
        Success status and new favorite state
    """
    try:
        from src.database_manager import db_manager
        from src.models.project_history import ProjectHistory

        # Initialize history database if needed
        await db_manager.initialize_history_database()

        session_factory = db_manager.get_history_session()

        async with session_factory() as session:
            result = await session.execute(
                select(ProjectHistory).where(ProjectHistory.id == project_id)
            )
            project = result.scalar_one_or_none()

            if project:
                project.is_favorite = not project.is_favorite
                await session.commit()
                return {
                    "success": True,
                    "isFavorite": project.is_favorite
                }

            return {
                "success": False,
                "error": "Project not found"
            }

    except Exception as e:
        print(f"[ProjectsRoute] Error toggling favorite: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao alternar favorito: {str(e)}")


class QuickSwitchRequest(BaseModel):
    """Request for quick project switch."""
    path: str


@router.post("/quick-switch")
async def quick_switch_project(request: QuickSwitchRequest):
    """
    Quick switch to a project from history.

    Args:
        request: Request with project path

    Returns:
        Success status and project info
    """
    try:
        from src.database_manager import db_manager
        from src.models.project_history import ProjectHistory

        # Load project using existing logic
        manager = get_project_manager()
        project = await manager.load_project(request.path)

        # Update active project in database
        async with async_session_maker() as session:
            # Clear previous active projects
            await session.execute(delete(ActiveProject))

            # Save new active project
            active_project = ActiveProject(
                id=project["id"],
                path=project["path"],
                name=project["name"],
                has_claude_config=project["has_claude_config"],
                claude_config_path=project["claude_config_path"],
            )
            session.add(active_project)
            await session.commit()

        return {
            "success": True,
            "project": project
        }

    except Exception as e:
        print(f"[ProjectsRoute] Error quick switching project: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao trocar projeto: {str(e)}")