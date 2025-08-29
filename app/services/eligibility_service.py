"""
Eligibility Service for NID Validation and Insurance Checking
Mock implementation for Rwanda NID and insurance systems (RSSB/CBHI)
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from enum import Enum

logger = logging.getLogger(__name__)


class MembershipTypeEnum(str, Enum):
    AFFILIATE = "affiliate"  # Primary member
    DEPENDANT = "dependant"  # Family member


class InsuranceStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class EligibilityService:
    """Mock eligibility service for NID validation and insurance checking"""
    
    def __init__(self):
        # Mock NID database (Rwanda NIDs are 16 digits)
        self.mock_nid_database = {
            "1198780123456789": {
                "first_name": "Jean",
                "last_name": "Uwimana", 
                "date_of_birth": "1998-07-01",
                "gender": "male",
                "district": "Gasabo",
                "sector": "Kacyiru"
            },
            "1197512345678901": {
                "first_name": "Marie",
                "last_name": "Mukamana",
                "date_of_birth": "1975-12-15", 
                "gender": "female",
                "district": "Nyarugenge",
                "sector": "Nyamirambo"
            },
            "1198503456789012": {
                "first_name": "Paul",
                "last_name": "Nkurunziza",
                "date_of_birth": "1985-03-22",
                "gender": "male", 
                "district": "Kicukiro",
                "sector": "Niboye"
            },
            "1199201234567890": {
                "first_name": "Grace",
                "last_name": "Uwizeye",
                "date_of_birth": "1992-11-08",
                "gender": "female",
                "district": "Gasabo", 
                "sector": "Remera"
            },
            "1198012345678901": {
                "first_name": "Emmanuel",
                "last_name": "Habimana",
                "date_of_birth": "1980-05-30",
                "gender": "male",
                "district": "Nyarugenge",
                "sector": "Muhima"
            }
        }
        
        # Mock insurance database - RSSB (formal sector)
        self.mock_rssb_database = {
            "1198780123456789": {
                "membership_type": MembershipTypeEnum.AFFILIATE,
                "policy_number": "RSSB-001234567",
                "status": InsuranceStatusEnum.ACTIVE,
                "coverage_percentage": "90%",
                "employer": "Bank of Kigali",
                "dependants": [
                    {
                        "nid": "1199812345678902", 
                        "name": "Alice Uwimana",
                        "relationship": "spouse",
                        "dob": "2000-03-15"
                    },
                    {
                        "nid": "1202012345678903",
                        "name": "David Uwimana", 
                        "relationship": "child",
                        "dob": "2020-08-22"
                    }
                ],
                "benefits": ["medical_consultation", "hospitalization", "surgery", "maternity", "dental"]
            },
            "1198012345678901": {
                "membership_type": MembershipTypeEnum.AFFILIATE,
                "policy_number": "RSSB-009876543", 
                "status": InsuranceStatusEnum.ACTIVE,
                "coverage_percentage": "95%",
                "employer": "Ministry of Health",
                "dependants": [
                    {
                        "nid": "1198512345678904",
                        "name": "Sarah Habimana",
                        "relationship": "spouse", 
                        "dob": "1985-12-10"
                    }
                ],
                "benefits": ["medical_consultation", "hospitalization", "surgery", "maternity", "dental", "optical"]
            }
        }
        
        # Mock insurance database - CBHI (community-based)
        self.mock_cbhi_database = {
            "1197512345678901": {
                "membership_type": MembershipTypeEnum.AFFILIATE,
                "policy_number": "CBHI-2024-001567",
                "status": InsuranceStatusEnum.ACTIVE,
                "coverage_percentage": "80%", 
                "category": "Category 2",
                "cell": "Nyamirambo",
                "dependants": [
                    {
                        "nid": "1199912345678905",
                        "name": "Joseph Mukamana",
                        "relationship": "child",
                        "dob": "1999-05-20"
                    },
                    {
                        "nid": "2001012345678906", 
                        "name": "Anne Mukamana",
                        "relationship": "child",
                        "dob": "2001-09-14"
                    }
                ],
                "benefits": ["medical_consultation", "basic_hospitalization", "maternity"]
            },
            "1198503456789012": {
                "membership_type": MembershipTypeEnum.DEPENDANT,
                "policy_number": "CBHI-2024-002890",
                "status": InsuranceStatusEnum.ACTIVE, 
                "coverage_percentage": "75%",
                "category": "Category 3",
                "cell": "Niboye",
                "primary_member": {
                    "nid": "1975012345678907",
                    "name": "Robert Nkurunziza",
                    "relationship": "father"
                },
                "benefits": ["medical_consultation", "basic_hospitalization"]
            },
            "1199201234567890": {
                "membership_type": MembershipTypeEnum.AFFILIATE,
                "policy_number": "CBHI-2024-003456", 
                "status": InsuranceStatusEnum.ACTIVE,
                "coverage_percentage": "70%",
                "category": "Category 1",
                "cell": "Remera",
                "dependants": [],
                "benefits": ["medical_consultation", "basic_hospitalization", "maternity"]
            }
        }
    
    async def validate_nid_and_insurance(self, nid: str, insurance_provider: str) -> Dict[str, Any]:
        """
        Validate NID and check insurance eligibility
        
        Args:
            nid: Rwanda National ID (16 digits)
            insurance_provider: Insurance provider (RSSB or CBHI)
            
        Returns:
            Dict containing personal details and insurance information
        """
        logger.info(f"Validating NID {nid} with insurance provider {insurance_provider}")
        
        # Validate NID format (Rwanda NIDs are 16 digits)
        if not self._validate_nid_format(nid):
            return {
                "success": False,
                "error": "Invalid NID format. Rwanda NID must be 16 digits.",
                "error_code": "INVALID_NID_FORMAT"
            }
        
        # Check if NID exists in mock database
        personal_details = self.mock_nid_database.get(nid)
        if not personal_details:
            return {
                "success": False,
                "error": "NID not found in national database.",
                "error_code": "NID_NOT_FOUND"
            }
        
        # Get insurance details based on provider
        insurance_details = None
        if insurance_provider.upper() == "RSSB":
            insurance_details = self.mock_rssb_database.get(nid)
        elif insurance_provider.upper() == "CBHI":
            insurance_details = self.mock_cbhi_database.get(nid)
        else:
            return {
                "success": False,
                "error": "Invalid insurance provider. Must be RSSB or CBHI.",
                "error_code": "INVALID_INSURANCE_PROVIDER"
            }
        
        if not insurance_details:
            return {
                "success": False,
                "error": f"No {insurance_provider} insurance found for this NID.",
                "error_code": "INSURANCE_NOT_FOUND"
            }
        
        # Calculate age
        dob = datetime.strptime(personal_details["date_of_birth"], "%Y-%m-%d").date()
        age = self._calculate_age(dob)
        
        # Build successful response
        response = {
            "success": True,
            "personal_details": {
                "nid": nid,
                "first_name": personal_details["first_name"],
                "last_name": personal_details["last_name"],
                "full_name": f"{personal_details['first_name']} {personal_details['last_name']}",
                "date_of_birth": personal_details["date_of_birth"],
                "age": age,
                "gender": personal_details["gender"],
                "district": personal_details.get("district"),
                "sector": personal_details.get("sector")
            },
            "insurance_details": {
                "provider": insurance_provider.upper(),
                "policy_number": insurance_details["policy_number"],
                "membership_type": insurance_details["membership_type"],
                "status": insurance_details["status"],
                "coverage_percentage": insurance_details["coverage_percentage"],
                "benefits": insurance_details["benefits"]
            }
        }
        
        # Add provider-specific details
        if insurance_provider.upper() == "RSSB":
            response["insurance_details"]["employer"] = insurance_details.get("employer")
            response["insurance_details"]["dependants"] = insurance_details.get("dependants", [])
            response["insurance_details"]["total_dependants"] = len(insurance_details.get("dependants", []))
            
        elif insurance_provider.upper() == "CBHI":
            response["insurance_details"]["category"] = insurance_details.get("category")
            response["insurance_details"]["cell"] = insurance_details.get("cell")
            
            if insurance_details["membership_type"] == MembershipTypeEnum.AFFILIATE:
                response["insurance_details"]["dependants"] = insurance_details.get("dependants", [])
                response["insurance_details"]["total_dependants"] = len(insurance_details.get("dependants", []))
            else:
                response["insurance_details"]["primary_member"] = insurance_details.get("primary_member")
        
        logger.info(f"Eligibility check successful for NID {nid}")
        return response
    
    def _validate_nid_format(self, nid: str) -> bool:
        """Validate Rwanda NID format (16 digits)"""
        if not nid:
            return False
        
        # Remove any spaces or dashes
        clean_nid = nid.replace(" ", "").replace("-", "")
        
        # Check if exactly 16 digits
        return len(clean_nid) == 16 and clean_nid.isdigit()
    
    def _calculate_age(self, birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    async def get_dependants(self, nid: str, insurance_provider: str) -> Dict[str, Any]:
        """Get list of dependants for a given NID and insurance provider"""
        # Get insurance details
        insurance_details = None
        if insurance_provider.upper() == "RSSB":
            insurance_details = self.mock_rssb_database.get(nid)
        elif insurance_provider.upper() == "CBHI":
            insurance_details = self.mock_cbhi_database.get(nid)
        
        if not insurance_details or insurance_details["membership_type"] != MembershipTypeEnum.AFFILIATE:
            return {
                "success": False,
                "error": "Only primary members (affiliates) can have dependants",
                "dependants": []
            }
        
        dependants = insurance_details.get("dependants", [])
        return {
            "success": True,
            "dependants": dependants,
            "total_dependants": len(dependants)
        }


# Global instance
eligibility_service = EligibilityService()