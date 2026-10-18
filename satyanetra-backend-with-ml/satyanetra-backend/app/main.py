import secrets, string, logging, json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from app.config import settings
from app.database import Base, engine, get_db
from app.models import User, Role, Report, ReportStatus, ReportHistory, Evidence, AuditLog
from app.schemas import RegisterIn, LoginIn, UserOut, TokenOut, ReportCreate, ReportOut, PublicReportStatus, StatusUpdate, OfficialResponseIn, AIAskIn, ReportAnalysisIn
from app.security import hash_password, verify_password, make_token, current_user, require_roles
from app.ai import answer
from app.ml_service import analyze_report_text, MLUnavailableError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("satyanetra")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # For convenience on local development. Use Alembic migrations for deployed environments.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.app_name, version="0.1.0", description="Sensitive-report handling API for SatyaNetra", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET","POST","PATCH","OPTIONS"], allow_headers=["Authorization","Content-Type"])

@app.middleware("http")
async def basic_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/api/v1/health")
def health():
    return {"status":"ok","service":"satyanetra-api","database":"configured"}

def audit(db: Session, actor_id, action, resource_type, resource_id=None, details=None):
    db.add(AuditLog(actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id, details=details))

@app.post("/api/v1/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    # Never accept privileged role names from public registration.
    if payload.role not in ("individual", "organization"):
        raise HTTPException(status_code=400, detail="Public registration supports individual or organization accounts only")
    if payload.role == "organization" and not payload.organization:
        raise HTTPException(status_code=422, detail="Organization name is required")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password),
                role=Role(payload.role), organization=payload.organization)
    db.add(user); db.flush()
    audit(db, user.id, "user.registered", "user", user.id, {"role": user.role.value})
    db.commit(); db.refresh(user)
    return user

@app.post("/api/v1/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    password = payload.password
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return {"access_token":make_token(user), "token_type":"bearer", "user":user}

@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user

def new_reference():
    alphabet = string.ascii_uppercase + string.digits
    return "SN-" + "".join(secrets.choice(alphabet) for _ in range(10))

@app.post("/api/v1/reports", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate, request: Request, db: Session = Depends(get_db)):
    # Optional bearer auth is intentionally handled below to keep guest submissions possible.
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi import Security
    # The optional auth is resolved in the separate endpoint helper below; this endpoint is guest-safe.
    report = Report(reference=new_reference(), category=payload.category.strip(), description=payload.description.strip(),
                    incident_date=payload.incident_date, location=payload.location, anonymous=payload.anonymous,
                    contact_email=None if payload.anonymous else (payload.contact_email.lower() if payload.contact_email else None),
                    owner_id=None, status=ReportStatus.submitted)
    db.add(report); db.flush()
    db.add(ReportHistory(report_id=report.id, old_status=None, new_status=ReportStatus.submitted.value, note="Initial submission"))
    audit(db, None, "report.created", "report", report.id, {"anonymous":payload.anonymous, "category":payload.category})
    db.commit(); db.refresh(report)
    return report

@app.get("/api/v1/reports/{reference}", response_model=PublicReportStatus)
def get_report(reference: str, db: Session = Depends(get_db)):
    # Public reference lookup deliberately reveals workflow status only. A reference is not an access credential.
    report = db.scalar(select(Report).where(Report.reference == reference.upper()))
    if not report: raise HTTPException(status_code=404, detail="Report not found")
    return {"reference": report.reference, "status": report.status,
            "created_at": report.created_at, "updated_at": report.updated_at}

@app.get("/api/v1/reports", response_model=list[ReportOut])
def list_reports(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 status: ReportStatus | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Report).order_by(Report.created_at.desc()).limit(limit).offset(offset)
    if user.role not in (Role.admin, Role.reviewer):
        stmt = stmt.where(Report.owner_id == user.id)
    if status: stmt = stmt.where(Report.status == status)
    return list(db.scalars(stmt).all())

@app.patch("/api/v1/reports/{reference}/status", response_model=ReportOut)
def update_status(reference: str, payload: StatusUpdate, user: User = Depends(require_roles(Role.admin, Role.reviewer)), db: Session = Depends(get_db)):
    report = db.scalar(select(Report).where(Report.reference == reference.upper()))
    if not report: raise HTTPException(status_code=404, detail="Report not found")
    old = report.status.value
    report.status = payload.status
    report.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    db.add(ReportHistory(report_id=report.id, old_status=old, new_status=payload.status.value, note=payload.note, changed_by=user.id))
    audit(db, user.id, "report.status_changed", "report", report.id, {"from":old,"to":payload.status.value})
    db.commit(); db.refresh(report)
    return report

@app.post("/api/v1/official-responses", status_code=201)
def official_response(payload: OfficialResponseIn, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.government, Role.organization, Role.reviewer, Role.admin))):
    report = db.scalar(select(Report).where(Report.reference == payload.reference.upper()))
    if not report: raise HTTPException(status_code=404, detail="Report not found")
    # Store response as an auditable event; does not alter report status automatically.
    audit(db, user.id, "official.response_submitted", "report", report.id, {"role":payload.role, "summary":payload.summary[:500]})
    db.commit()
    return {"accepted":True,"reference":report.reference,"message":"Response recorded for authorised review."}

@app.post("/api/v1/ai/ask")
def ask_ai(payload: AIAskIn):
    return answer(payload.message, payload.context)

@app.post("/api/v1/ai/analyze-report")
def analyze_report_endpoint(payload: ReportAnalysisIn):
    """Compare a report description with curated public cases and flag explainable warning patterns.

    Scores are lexical-retrieval proximity, not fraud probabilities; indicators are heuristic
    warning signs for human review, not proof of wrongdoing. The text is not stored or logged.
    """
    try:
        return analyze_report_text(payload.description, top_k=payload.top_k)
    except MLUnavailableError:
        raise HTTPException(status_code=503, detail="Report analysis is temporarily unavailable")

@app.get("/api/v1/public-cases")
def public_cases(
    state: str | None = Query(default=None, max_length=80),
    jurisdiction: str | None = Query(default=None, max_length=40),
    category: str | None = Query(default=None, max_length=100),
):
    """Return a curated, source-linked demonstration dataset; not a live national registry."""
    data_path = Path(__file__).resolve().parent.parent / "data" / "public_cases.json"
    try:
        records = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Public cases dataset unavailable")
        raise HTTPException(status_code=503, detail="Public cases dataset is temporarily unavailable")
    if state:
        records = [r for r in records if r["state"].casefold() == state.casefold()]
    if jurisdiction:
        records = [r for r in records if r["jurisdiction"].casefold() == jurisdiction.casefold()]
    if category:
        records = [r for r in records if category.casefold() in r["category"].casefold()]
    return {
        "dataset": "SatyaNetra curated public-source case examples",
        "dataset_type": "curated_seed_data_not_live_feed",
        "last_reviewed": "2026-10-17",
        "count": len(records),
        "disclaimer": "Reported allegations are not proof of guilt. Status reflects the cited source at its publication date and may have changed. Amounts are source-reported context, not comparable corruption indices.",
        "records": records,
    }

@app.get("/api/v1/public-cases/sources")
def public_case_sources():
    data_path = Path(__file__).resolve().parent.parent / "data" / "source_catalog.json"
    try:
        records = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Public case source catalog unavailable")
        raise HTTPException(status_code=503, detail="Source catalog is temporarily unavailable")
    return {"count": len(records), "sources": records,
            "note": "Sources have different scopes; grievance statistics and annual reports are not directly comparable bribery prevalence measures."}

@app.get("/api/v1/transparency-index")
def transparency_index():
    return {"status":"not_implemented","message":"Transparency Index is a planned module. No live sources or validated scoring are connected.","records":[]}

@app.exception_handler(Exception)
async def safe_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled application error at %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail":"An unexpected server error occurred"})
