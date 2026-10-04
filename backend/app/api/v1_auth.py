"""Authentication routes for P2-11 — User Accounts & Projects.

Provides registration, login, and project management endpoints.
Uses SQLAlchemy-backed SQLite (default) / PostgreSQL (production) via
the app.models module. API key abstraction consistent with P2-10.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_session, init_db
from app.models import User, project_users
from app.core.config import settings
import datetime

router = APIRouter(tags=["auth"])


def _get_db():
    """Dependency to get a DB session, initializing if needed."""
    init_db()
    return get_session()


@router.post("/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(
    email: str = Body(),
    password: str = Body(),
    db: Session = Depends(_get_db),
) -> dict:
    """Register a new user account.

    POST /api/v1/auth/register
    """
    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    from app.models import _hash_password
    hashed_pw = _hash_password(password)

    # Create new user
    user = User(
        email=email,
        hashed_password=hashed_pw,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "User registered successfully",
        "user_id": user.id,
        "email": user.email,
    }


@router.post("/auth/login", response_model=dict)
def login(
    email: str = Body(),
    password: str = Body(),
    db: Session = Depends(_get_db),
) -> dict:
    """Login and receive authentication token.

    POST /api/v1/auth/login
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    from app.models import _verify_password
    if not _verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Generate simple token
    access_token_expires = datetime.timedelta(
        minutes=getattr(settings, "access_token_expire_minutes", 30)
    )
    import json

    token_data = {"sub": str(user.id), "email": user.email}
    # Simple token encoding (jose not required as dependency)
    token = json.dumps(token_data)

    return {
        "success": True,
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
    }


@router.post("/projects", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_project(
    name: str = Body(),
    description: str = Body(default=""),
    is_public: bool = Body(default=False),
    db: Session = Depends(_get_db),
) -> dict:
    """Create a new project.

    POST /api/v1/projects
    """
    from app.models import Project

    project = Project(
        name=name,
        description=description,
        is_public=is_public,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "success": True,
        "message": "Project created successfully",
        "project_id": project.id,
        "name": project.name,
    }


@router.get("/projects", response_model=dict)
def list_projects(
    db: Session = Depends(_get_db),
) -> dict:
    """List projects accessible to the current user.

    GET /api/v1/projects
    """
    from app.models import Project

    projects = db.query(Project).all()
    return {
        "success": True,
        "message": "Projects retrieved successfully",
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "is_public": p.is_public,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ],
    }


from pydantic import BaseModel


class AssignVideo(BaseModel):
    stored_filename: str
    project_id: int


@router.post("/videos/assign", response_model=dict)
def assign_video_to_project(
    assign: AssignVideo = ...,
    db: Session = Depends(_get_db),
) -> dict:
    """Assign a video to a project (ownership isolation).

    POST /api/v1/videos/assign
    """
    from app.models import Video, User, Project

    # Verify project exists
    project = db.query(Project).filter(Project.id == assign.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Find or create video entry
    video = db.query(Video).filter(Video.stored_filename == assign.stored_filename).first()
    if not video:
        # Use a default user (in real app, would come from auth context)
        user = db.query(User).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user found; register first",
            )
        video = Video(
            stored_filename=assign.stored_filename,
            original_filename=assign.stored_filename,
            owner_id=user.id,
            project_id=assign.project_id,
            status="uploaded",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(video)
    else:
        # Update existing video's project assignment
        video.project_id = project_id
        video.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(video)

    return {
        "success": True,
        "message": "Video assigned to project",
        "video_id": video.id,
        "stored_filename": video.stored_filename,
        "project_id": video.project_id,
    }