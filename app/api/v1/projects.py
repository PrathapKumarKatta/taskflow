from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.dependencies import DB, CurrentUser
from app.models import Project, Status, Task, utcnow
from app.schemas import Page, ProjectCreate, ProjectRead, ProjectStats
from app.services.permissions import (
    lock_workspace,
    project_access,
    require_manager,
    workspace_access,
)

router = APIRouter(tags=["Projects"])


@router.get("/projects/{project_id}/stats", response_model=ProjectStats)
async def stats(project_id: UUID, db: DB, user: CurrentUser):
    await project_access(db, project_id, user)
    rows = (
        await db.execute(
            select(Task.status, func.count())
            .where(Task.project_id == project_id)
            .group_by(Task.status)
        )
    ).all()
    counts = dict.fromkeys(Status, 0)
    counts.update(dict(rows))
    overdue, my_open = (
        await db.execute(
            select(
                func.count().filter(Task.status != Status.done, Task.due_at < utcnow()),
                func.count().filter(Task.status != Status.done, Task.assignee_id == user.id),
            ).where(Task.project_id == project_id)
        )
    ).one()
    return {
        "total": sum(counts.values()),
        "by_status": counts,
        "overdue": overdue,
        "my_open": my_open,
    }


@router.post("/workspaces/{workspace_id}/projects", response_model=ProjectRead, status_code=201)
async def create(workspace_id: UUID, data: ProjectCreate, db: DB, user: CurrentUser):
    await lock_workspace(db, workspace_id)
    member = await workspace_access(db, workspace_id, user)
    require_manager(member)
    project = Project(**data.model_dump(), workspace_id=workspace_id, created_by=user.id)
    db.add(project)
    await db.flush()
    return project


@router.get("/workspaces/{workspace_id}/projects", response_model=Page[ProjectRead])
async def listing(
    workspace_id: UUID,
    db: DB,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    await workspace_access(db, workspace_id, user)
    query = select(Project).where(Project.workspace_id == workspace_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (
        await db.scalars(
            query.order_by(Project.created_at.desc(), Project.id.desc()).limit(limit).offset(offset)
        )
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
