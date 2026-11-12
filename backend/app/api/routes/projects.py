from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...domain.projects import Project, ProjectCreate, ProjectSummary
from ...domain.templates import get_template
from ...runtime.state import AppState
from ..deps import get_state

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
def list_projects(state: AppState = Depends(get_state)) -> list[ProjectSummary]:
    return [
        ProjectSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            default_template_id=p.default_template_id,
            mission_count=len(p.mission_ids),
            updated_at=p.updated_at,
        )
        for p in state.projects.list()
    ]


@router.post("", response_model=Project)
def create_project(body: ProjectCreate, state: AppState = Depends(get_state)) -> Project:
    if not body.name.strip():
        raise HTTPException(400, "name required")
    if get_template(body.default_template_id) is None:
        raise HTTPException(400, "unknown template")
    project = Project(
        name=body.name.strip(),
        description=body.description.strip(),
        default_template_id=body.default_template_id,
        default_stack=body.default_stack.strip() or "Python FastAPI + React",
    )
    return state.projects.save(project)


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str, state: AppState = Depends(get_state)) -> Project:
    project = state.projects.get(project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, state: AppState = Depends(get_state)) -> dict[str, bool]:
    if not state.projects.delete(project_id):
        raise HTTPException(404, "project not found")
    return {"ok": True}
