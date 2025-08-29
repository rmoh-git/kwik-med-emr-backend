"""
Eligibility API Endpoints for NID Validation and Insurance Checking
"""
import logging
from fastapi import APIRouter, HTTPException, status
from app.services.eligibility_service import eligibility_service
from app.schemas.eligibility import (
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    DependantsRequest,
    DependantsResponse,
    InsuranceValidationRequest,
    InsuranceValidationResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/check", response_model=EligibilityCheckResponse, status_code=status.HTTP_200_OK)
async def check_eligibility(request: EligibilityCheckRequest):
    """
    Check eligibility by validating NID and insurance information
    
    This endpoint:
    1. Validates the NID format and existence
    2. Retrieves personal details (name, DOB, gender)
    3. Checks insurance coverage and details
    4. Returns membership type (affiliate/dependant) and dependants information
    """
    logger.info(f"Eligibility check requested for NID: {request.nid[-4:]}**** with provider: {request.insurance_provider}")
    
    try:
        result = await eligibility_service.validate_nid_and_insurance(
            nid=request.nid,
            insurance_provider=request.insurance_provider
        )
        
        if not result["success"]:
            logger.warning(f"Eligibility check failed: {result.get('error_code', 'Unknown error')}")
            
            # Return structured error response
            return EligibilityCheckResponse(
                success=False,
                error=result["error"],
                error_code=result["error_code"]
            )
        
        # Convert to response model
        response = EligibilityCheckResponse(**result)
        logger.info(f"Eligibility check successful for {result['personal_details']['full_name']}")
        
        return response
        
    except Exception as e:
        logger.error(f"Eligibility check failed with exception: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eligibility check failed: {str(e)}"
        )


@router.post("/dependants", response_model=DependantsResponse, status_code=status.HTTP_200_OK)
async def get_dependants(request: DependantsRequest):
    """
    Get list of dependants for a primary member (affiliate)
    
    Returns all dependants associated with the given NID and insurance provider.
    Only works for primary members (affiliates), not dependants themselves.
    """
    logger.info(f"Dependants lookup requested for NID: {request.nid[-4:]}**** with provider: {request.insurance_provider}")
    
    try:
        result = await eligibility_service.get_dependants(
            nid=request.nid,
            insurance_provider=request.insurance_provider
        )
        
        response = DependantsResponse(**result)
        logger.info(f"Dependants lookup completed: {response.total_dependants} dependants found")
        
        return response
        
    except Exception as e:
        logger.error(f"Dependants lookup failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dependants lookup failed: {str(e)}"
        )


@router.post("/validate-insurance", response_model=InsuranceValidationResponse, status_code=status.HTTP_200_OK)
async def validate_insurance_only(request: InsuranceValidationRequest):
    """
    Quick insurance validation without full eligibility check
    
    Returns basic insurance status and coverage information without personal details.
    Useful for quick insurance verification.
    """
    logger.info(f"Insurance validation requested for NID: {request.nid[-4:]}**** with provider: {request.insurance_provider}")
    
    try:
        # Get full eligibility check first
        result = await eligibility_service.validate_nid_and_insurance(
            nid=request.nid,
            insurance_provider=request.insurance_provider
        )
        
        if not result["success"]:
            return InsuranceValidationResponse(
                valid=False,
                error=result["error"]
            )
        
        insurance_details = result["insurance_details"]
        
        return InsuranceValidationResponse(
            valid=True,
            policy_number=insurance_details["policy_number"],
            status=insurance_details["status"],
            coverage_percentage=insurance_details["coverage_percentage"]
        )
        
    except Exception as e:
        logger.error(f"Insurance validation failed: {str(e)}", exc_info=True)
        return InsuranceValidationResponse(
            valid=False,
            error=f"Insurance validation failed: {str(e)}"
        )


@router.get("/providers", status_code=status.HTTP_200_OK)
async def get_insurance_providers():
    """
    Get list of supported insurance providers
    """
    return {
        "providers": [
            {
                "code": "RSSB",
                "name": "Rwanda Social Security Board",
                "type": "formal_sector",
                "description": "For employees in formal sector"
            },
            {
                "code": "CBHI", 
                "name": "Community Based Health Insurance",
                "type": "community",
                "description": "Community-based insurance scheme"
            }
        ]
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check for eligibility service"""
    return {
        "status": "healthy",
        "service": "eligibility_service",
        "mock_nids_available": 5,
        "providers_supported": ["RSSB", "CBHI"]
    }