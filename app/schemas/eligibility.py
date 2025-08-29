"""
Eligibility API Schemas for NID Validation and Insurance Checking
"""
from datetime import date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class MembershipTypeEnum(str, Enum):
    AFFILIATE = "affiliate"
    DEPENDANT = "dependant"


class InsuranceStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class InsuranceProviderEnum(str, Enum):
    RSSB = "RSSB"
    CBHI = "CBHI"


class EligibilityCheckRequest(BaseModel):
    nid: str = Field(..., min_length=16, max_length=16, description="Rwanda National ID (16 digits)")
    insurance_provider: InsuranceProviderEnum = Field(..., description="Insurance provider (RSSB or CBHI)")


class PersonalDetails(BaseModel):
    nid: str
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: str
    age: int
    gender: str
    district: Optional[str] = None
    sector: Optional[str] = None


class Dependant(BaseModel):
    nid: str
    name: str
    relationship: str  # spouse, child, parent, etc.
    dob: str


class PrimaryMember(BaseModel):
    nid: str
    name: str
    relationship: str


class InsuranceDetails(BaseModel):
    provider: str
    policy_number: str
    membership_type: MembershipTypeEnum
    status: InsuranceStatusEnum
    coverage_percentage: str
    benefits: List[str]
    
    # RSSB-specific fields
    employer: Optional[str] = None
    dependants: Optional[List[Dependant]] = None
    total_dependants: Optional[int] = None
    
    # CBHI-specific fields
    category: Optional[str] = None
    cell: Optional[str] = None
    primary_member: Optional[PrimaryMember] = None


class EligibilityCheckResponse(BaseModel):
    success: bool
    personal_details: Optional[PersonalDetails] = None
    insurance_details: Optional[InsuranceDetails] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class DependantsRequest(BaseModel):
    nid: str = Field(..., min_length=16, max_length=16, description="Rwanda National ID (16 digits)")
    insurance_provider: InsuranceProviderEnum = Field(..., description="Insurance provider (RSSB or CBHI)")


class DependantsResponse(BaseModel):
    success: bool
    dependants: List[Dependant] = []
    total_dependants: int = 0
    error: Optional[str] = None


class InsuranceValidationRequest(BaseModel):
    """Request for validating insurance without full eligibility check"""
    nid: str = Field(..., min_length=16, max_length=16)
    insurance_provider: InsuranceProviderEnum


class InsuranceValidationResponse(BaseModel):
    """Response for insurance validation"""
    valid: bool
    policy_number: Optional[str] = None
    status: Optional[InsuranceStatusEnum] = None
    coverage_percentage: Optional[str] = None
    error: Optional[str] = None