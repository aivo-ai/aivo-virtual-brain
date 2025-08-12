from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ProvisionSource(str, Enum):
    DISTRICT = "district"
    PARENT = "parent"


class LearnerProfile(BaseModel):
    learner_temp_id: str
    first_name: str
    last_name: str
    email: str
    grade_level: Optional[int] = None


class EnrollmentContext(BaseModel):
    tenant_id: Optional[str] = None
    district_code: Optional[str] = None
    school_code: Optional[str] = None
    referral_source: Optional[str] = None


class EnrollmentRequest(BaseModel):
    learner_profile: LearnerProfile
    context: EnrollmentContext


class EnrollmentDecisionResponse(BaseModel):
    provision_source: ProvisionSource
    learner_temp_id: str
    tenant_id: Optional[str] = None
    checkout_url: Optional[str] = None
    seat_allocation_id: Optional[str] = None


app = FastAPI(
    title="Enrollment Router Service",
    description="Routes learner enrollment between district and parent flows",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/enroll")
def route_enrollment(request: EnrollmentRequest) -> EnrollmentDecisionResponse:
    """Route enrollment based on tenant context"""

    if request.context.tenant_id:
        # District/School path - allocate seat
        return EnrollmentDecisionResponse(
            provision_source=ProvisionSource.DISTRICT,
            learner_temp_id=request.learner_profile.learner_temp_id,
            tenant_id=request.context.tenant_id,
            seat_allocation_id=f"seat_{request.learner_profile.learner_temp_id}"
        )
    else:
        # Parent path - redirect to checkout
        return EnrollmentDecisionResponse(
            provision_source=ProvisionSource.PARENT,
            learner_temp_id=request.learner_profile.learner_temp_id,
            checkout_url="https://checkout.aivo.com/trial"
        )


@app.get("/health")
def health():
    return {"status": "healthy", "service": "enrollment-router"}


@app.get("/")
def root():
    return {
        "service": "Enrollment Router",
        "version": "1.0.0",
        "description": "Routes learner enrollment between district and parent flows"
    }
