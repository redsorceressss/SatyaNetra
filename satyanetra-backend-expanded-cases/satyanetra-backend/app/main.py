
import secrets
import string
import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.database import Base, engine, get_db
from app.models import (
    User,
    Role,
    Report,
    ReportStatus,
    ReportHistory,
    AuditLog,
)
from app.schemas import (
    RegisterIn,
    LoginIn,
    UserOut,
    TokenOut,
    ReportCreate,
    ReportOut,
    PublicReportStatus,
    StatusUpdate,
    OfficialResponseIn,
    AIAskIn,
)
from app.security import (
    hash_password,
    verify_password,
    make_token,
    current_user,
    require_roles,
)
from app.ai import answer


# --------------------------------------------------
# Configuration
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("satyanetra")

# Allows guest submissions and optional bearer authentication.
optional_bearer = HTTPBearer(auto_error=False)


# --------------------------------------------------
# Application lifecycle
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Suitable for local development.
    # Use database migrations in production.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Sensitive-report handling API for SatyaNetra",
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# --------------------------------------------------
# Security headers
# --------------------------------------------------

@app.middleware("http")
async def basic_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"

    return response


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "service": "satyanetra-api",
        "database": "configured",
    }


# --------------------------------------------------
# Audit logging
# --------------------------------------------------

def audit(
    db: Session,
    actor_id,
    action,
    resource_type,
    resource_id=None,
    details=None,
):
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
    )


# --------------------------------------------------
# Register
# --------------------------------------------------

@app.post(
    "/api/v1/auth/register",
    response_model=UserOut,
    status_code=201,
)
def register(
    payload: RegisterIn,
    db: Session = Depends(get_db),
):
    email = str(payload.email).lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists",
        )

    # Public registration cannot create privileged accounts.
    if payload.role not in ("individual", "organization"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Public registration supports individual "
                "or organization accounts only"
            ),
        )

    if payload.role == "organization" and not payload.organization:
        raise HTTPException(
            status_code=422,
            detail="Organization name is required",
        )

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=Role(payload.role),
        organization=payload.organization,
    )

    db.add(user)
    db.flush()

    audit(
        db,
        user.id,
        "user.registered",
        "user",
        user.id,
        {"role": user.role.value},
    )

    db.commit()
    db.refresh(user)

    return user


# --------------------------------------------------
# Login
# --------------------------------------------------

@app.post(
    "/api/v1/auth/login",
    response_model=TokenOut,
)
def login(
    payload: LoginIn,
    db: Session = Depends(get_db),
):
    email = str(payload.email).lower()
    password = payload.password

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if not user or not verify_password(
        password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account disabled",
        )

    return {
        "access_token": make_token(user),
        "token_type": "bearer",
        "user": user,
    }


# --------------------------------------------------
# Current authenticated user
# --------------------------------------------------

@app.get(
    "/api/v1/auth/me",
    response_model=UserOut,
)
def me(
    user: User = Depends(current_user),
):
    return user


# --------------------------------------------------
# Generate report reference
# --------------------------------------------------

def new_reference():
    alphabet = string.ascii_uppercase + string.digits

    return "SN-" + "".join(
        secrets.choice(alphabet)
        for _ in range(10)
    )


# --------------------------------------------------
# Create report
# --------------------------------------------------

@app.post(
    "/api/v1/reports",
    response_model=ReportOut,
    status_code=201,
)
def create_report(
    payload: ReportCreate,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        optional_bearer
    ),
    db: Session = Depends(get_db),
):
    # Guest submissions are supported.
    # If a token is supplied, validate it.
    owner = (
        current_user(credentials.credentials, db)
        if credentials is not None
        else None
    )

    # Keep anonymous reports unlinked to an account.
    # Link non-anonymous reports to the authenticated owner.
    owner_id = (
        owner.id
        if owner is not None and not payload.anonymous
        else None
    )

    report = Report(
        reference=new_reference(),
        category=payload.category.strip(),
        description=payload.description.strip(),
        incident_date=payload.incident_date,
        location=payload.location,
        anonymous=payload.anonymous,
        contact_email=(
            None
            if payload.anonymous
            else (
                payload.contact_email.lower()
                if payload.contact_email
                else None
            )
        ),
        owner_id=owner_id,
        status=ReportStatus.submitted,
    )

    db.add(report)
    db.flush()

    db.add(
        ReportHistory(
            report_id=report.id,
            old_status=None,
            new_status=ReportStatus.submitted.value,
            note="Initial submission",
        )
    )

    audit(
        db,
        owner.id if owner is not None else None,
        "report.created",
        "report",
        report.id,
        {
            "anonymous": payload.anonymous,
            "category": payload.category,
        },
    )

    db.commit()
    db.refresh(report)

    return report


# --------------------------------------------------
# Public report status lookup
# --------------------------------------------------

@app.get(
    "/api/v1/reports/{reference}",
    response_model=PublicReportStatus,
)
def get_report(
    reference: str,
    db: Session = Depends(get_db),
):
    report = db.scalar(
        select(Report).where(
            Report.reference == reference.upper()
        )
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return {
        "reference": report.reference,
        "status": report.status,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


# --------------------------------------------------
# List reports
# --------------------------------------------------

@app.get(
    "/api/v1/reports",
    response_model=list[ReportOut],
)
def list_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: ReportStatus | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Report).order_by(
        Report.created_at.desc()
    )

    # Regular users see only their own linked reports.
    # Reviewers and admins can see reports across users.
    if user.role not in (Role.admin, Role.reviewer):
        stmt = stmt.where(
            Report.owner_id == user.id
        )

    if status is not None:
        stmt = stmt.where(
            Report.status == status
        )

    stmt = stmt.limit(limit).offset(offset)

    return list(db.scalars(stmt).all())


# --------------------------------------------------
# Update report status
# --------------------------------------------------

@app.patch(
    "/api/v1/reports/{reference}/status",
    response_model=ReportOut,
)
def update_status(
    reference: str,
    payload: StatusUpdate,
    user: User = Depends(
        require_roles(Role.admin, Role.reviewer)
    ),
    db: Session = Depends(get_db),
):
    report = db.scalar(
        select(Report).where(
            Report.reference == reference.upper()
        )
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    old_status = report.status.value

    report.status = payload.status
    report.updated_at = datetime.now(timezone.utc)

    db.add(
        ReportHistory(
            report_id=report.id,
            old_status=old_status,
            new_status=payload.status.value,
            note=payload.note,
            changed_by=user.id,
        )
    )

    audit(
        db,
        user.id,
        "report.status_changed",
        "report",
        report.id,
        {
            "from": old_status,
            "to": payload.status.value,
        },
    )

    db.commit()
    db.refresh(report)

    return report


# --------------------------------------------------
# Official responses
# --------------------------------------------------

@app.post(
    "/api/v1/official-responses",
    status_code=201,
)
def official_response(
    payload: OfficialResponseIn,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.government,
            Role.organization,
            Role.reviewer,
            Role.admin,
        )
    ),
):
    report = db.scalar(
        select(Report).where(
            Report.reference == payload.reference.upper()
        )
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    # Record an auditable event without automatically
    # changing the report status.
    audit(
        db,
        user.id,
        "official.response_submitted",
        "report",
        report.id,
        {
            "role": payload.role,
            "summary": payload.summary[:500],
        },
    )

    db.commit()

    return {
        "accepted": True,
        "reference": report.reference,
        "message": (
            "Response recorded for authorised review."
        ),
    }


# --------------------------------------------------
# AI assistant
# --------------------------------------------------

@app.post("/api/v1/ai/ask")
def ask_ai(
    payload: AIAskIn,
):
    return answer(
        payload.message,
        payload.context,
    )


# --------------------------------------------------
# Curated public cases
# --------------------------------------------------

@app.get("/api/v1/public-cases")
def public_cases(
    state: str | None = Query(
        default=None,
        max_length=80,
    ),
    jurisdiction: str | None = Query(
        default=None,
        max_length=40,
    ),
    category: str | None = Query(
        default=None,
        max_length=100,
    ),
):
    """
    Return curated, source-linked demonstration cases.
    This is not a live national registry.
    """

    data_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "public_cases.json"
    )

    try:
        records = json.loads(
            data_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        logger.exception(
            "Public cases dataset unavailable"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Public cases dataset is temporarily unavailable"
            ),
        )

    if state:
        records = [
            record
            for record in records
            if record["state"].casefold() == state.casefold()
        ]

    if jurisdiction:
        records = [
            record
            for record in records
            if record["jurisdiction"].casefold()
            == jurisdiction.casefold()
        ]

    if category:
        records = [
            record
            for record in records
            if category.casefold()
            in record["category"].casefold()
        ]

    return {
        "dataset": (
            "SatyaNetra curated public-source case examples"
        ),
        "dataset_type": "curated_seed_data_not_live_feed",
        "last_reviewed": "2026-10-17",
        "count": len(records),
        "disclaimer": (
            "Reported allegations are not proof of guilt. "
            "Status reflects the cited source at its publication "
            "date and may have changed. Amounts are source-reported "
            "context, not comparable corruption indices."
        ),
        "records": records,
    }


# --------------------------------------------------
# Public case source catalogue
# --------------------------------------------------

@app.get("/api/v1/public-cases/sources")
def public_case_sources():
    data_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "source_catalog.json"
    )

    try:
        records = json.loads(
            data_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        logger.exception(
            "Public case source catalog unavailable"
        )
        raise HTTPException(
            status_code=503,
            detail="Source catalog is temporarily unavailable",
        )

    return {
        "count": len(records),
        "sources": records,
        "note": (
            "Sources have different scopes; grievance statistics "
            "and annual reports are not directly comparable "
            "bribery prevalence measures."
        ),
    }


# --------------------------------------------------
# Transparency index placeholder
# --------------------------------------------------

@app.get("/api/v1/transparency-index")
def transparency_index():
    return {
        "status": "not_implemented",
        "message": (
            "Transparency Index is a planned module. "
            "No live sources or validated scoring are connected."
        ),
        "records": [],
    }


# --------------------------------------------------
# Safe unexpected error handler
# --------------------------------------------------

@app.exception_handler(Exception)
async def safe_unexpected_error(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled application error at %s",
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected server error occurred"
        },
    )
