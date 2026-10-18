from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models import Role, ReportStatus

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(default="individual") # only individual/organization accepted at public registration
    organization: str | None = Field(default=None, max_length=180)

class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    organization: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ReportCreate(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=20, max_length=12000)
    incident_date: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=240)
    anonymous: bool = True
    contact_email: EmailStr | None = None

class ReportOut(BaseModel):
    id: str
    reference: str
    category: str
    description: str
    incident_date: str | None
    location: str | None
    anonymous: bool
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class StatusUpdate(BaseModel):
    status: ReportStatus
    note: str | None = Field(default=None, max_length=2000)

class OfficialResponseIn(BaseModel):
    reference: str = Field(min_length=6, max_length=24)
    summary: str = Field(min_length=10, max_length=6000)
    role: str = Field(min_length=2, max_length=120)
    confirmation: bool

class AIAskIn(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    context: str | None = Field(default=None, max_length=3000)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class PublicReportStatus(BaseModel):
    reference: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    message: str = "Status only; sensitive report details are not publicly available."
