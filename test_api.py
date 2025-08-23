#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Horizon 1000 Health Provider API
Tests all endpoints with real data scenarios
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import httpx

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

class APITester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "test_details": []
        }
        self.created_resources = {
            "patients": [],
            "sessions": [],
            "recordings": [],
            "analyses": []
        }
    
    def log_test(self, test_name: str, passed: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.test_results["total_tests"] += 1
        if passed:
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {details}")
        
        self.test_results["test_details"].append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "response_data": response_data if passed else None,
            "timestamp": datetime.now().isoformat()
        })
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    Details: {details}")
    
    async def test_health_endpoint(self, client: httpx.AsyncClient):
        """Test health check endpoint"""
        try:
            response = await client.get(f"{self.base_url}/health")
            passed = response.status_code == 200 and "status" in response.json()
            self.log_test(
                "Health Check", 
                passed, 
                f"Status: {response.status_code}, Response: {response.json()}"
            )
            return passed
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False
    
    async def test_root_endpoint(self, client: httpx.AsyncClient):
        """Test root endpoint"""
        try:
            response = await client.get(f"{self.base_url}/")
            passed = response.status_code == 200 and "message" in response.json()
            self.log_test(
                "Root Endpoint", 
                passed, 
                f"Status: {response.status_code}, Response: {response.json()}"
            )
            return passed
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Exception: {str(e)}")
            return False
    
    async def test_patient_endpoints(self, client: httpx.AsyncClient):
        """Test all patient endpoints"""
        test_patients = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1980-05-15T00:00:00",
                "gender": "male",
                "phone": "+1234567890",
                "email": "john.doe@example.com",
                "address": "123 Main St, Anytown, USA"
            },
            {
                "first_name": "Jane",
                "last_name": "Smith", 
                "date_of_birth": "1992-08-22T00:00:00",
                "gender": "female",
                "phone": "+1987654321",
                "email": "jane.smith@example.com"
            }
        ]
        
        # Test creating patients
        for i, patient_data in enumerate(test_patients):
            try:
                response = await client.post(f"{self.api_url}/patients/", json=patient_data)
                passed = response.status_code == 201
                if passed:
                    created_patient = response.json()
                    self.created_resources["patients"].append(created_patient["id"])
                    self.log_test(
                        f"Create Patient {i+1}", 
                        True, 
                        f"Created patient with ID: {created_patient['id']}, MRN: {created_patient['medical_record_number']}",
                        created_patient
                    )
                else:
                    self.log_test(
                        f"Create Patient {i+1}", 
                        False, 
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
            except Exception as e:
                self.log_test(f"Create Patient {i+1}", False, f"Exception: {str(e)}")
        
        # Test getting a patient
        if self.created_resources["patients"]:
            patient_id = self.created_resources["patients"][0]
            try:
                response = await client.get(f"{self.api_url}/patients/{patient_id}")
                passed = response.status_code == 200
                patient_data = response.json() if passed else None
                self.log_test(
                    "Get Patient", 
                    passed, 
                    f"Retrieved patient: {patient_data.get('first_name', '')} {patient_data.get('last_name', '')}" if passed else f"Status: {response.status_code}",
                    patient_data
                )
            except Exception as e:
                self.log_test("Get Patient", False, f"Exception: {str(e)}")
        
        # Test searching patients
        try:
            response = await client.get(f"{self.api_url}/patients/search?query=John")
            passed = response.status_code == 200
            search_results = response.json() if passed else None
            self.log_test(
                "Search Patients", 
                passed, 
                f"Found {search_results.get('total', 0)} patients" if passed else f"Status: {response.status_code}",
                search_results
            )
        except Exception as e:
            self.log_test("Search Patients", False, f"Exception: {str(e)}")
        
        # Test listing patients
        try:
            response = await client.get(f"{self.api_url}/patients/?limit=5")
            passed = response.status_code == 200
            patients_list = response.json() if passed else None
            self.log_test(
                "List Patients", 
                passed, 
                f"Retrieved {len(patients_list) if patients_list else 0} patients" if passed else f"Status: {response.status_code}",
                patients_list
            )
        except Exception as e:
            self.log_test("List Patients", False, f"Exception: {str(e)}")
        
        # Test updating a patient
        if self.created_resources["patients"]:
            patient_id = self.created_resources["patients"][0]
            update_data = {"phone": "+1111111111", "address": "456 Oak Ave, Newtown, USA"}
            try:
                response = await client.put(f"{self.api_url}/patients/{patient_id}", json=update_data)
                passed = response.status_code == 200
                updated_patient = response.json() if passed else None
                self.log_test(
                    "Update Patient", 
                    passed, 
                    f"Updated patient phone to {updated_patient.get('phone', '')}" if passed else f"Status: {response.status_code}",
                    updated_patient
                )
            except Exception as e:
                self.log_test("Update Patient", False, f"Exception: {str(e)}")
    
    async def test_session_endpoints(self, client: httpx.AsyncClient):
        """Test all session endpoints"""
        if not self.created_resources["patients"]:
            self.log_test("Create Session", False, "No patients available for session creation")
            return
        
        patient_id = self.created_resources["patients"][0]
        session_data = {
            "patient_id": patient_id,
            "practitioner_name": "Dr. Sarah Wilson",
            "practitioner_id": "PRAC001",
            "visit_type": "General Consultation",
            "chief_complaint": "Regular checkup and health assessment"
        }
        
        # Test creating a session
        try:
            response = await client.post(f"{self.api_url}/sessions/", json=session_data)
            passed = response.status_code == 201
            if passed:
                created_session = response.json()
                self.created_resources["sessions"].append(created_session["id"])
                self.log_test(
                    "Create Session", 
                    True, 
                    f"Created session with ID: {created_session['id']}",
                    created_session
                )
            else:
                self.log_test(
                    "Create Session", 
                    False, 
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            self.log_test("Create Session", False, f"Exception: {str(e)}")
        
        # Test getting a session
        if self.created_resources["sessions"]:
            session_id = self.created_resources["sessions"][0]
            try:
                response = await client.get(f"{self.api_url}/sessions/{session_id}")
                passed = response.status_code == 200
                session_data = response.json() if passed else None
                self.log_test(
                    "Get Session", 
                    passed, 
                    f"Retrieved session for practitioner: {session_data.get('practitioner_name', '')}" if passed else f"Status: {response.status_code}",
                    session_data
                )
            except Exception as e:
                self.log_test("Get Session", False, f"Exception: {str(e)}")
        
        # Test getting patient sessions
        try:
            response = await client.get(f"{self.api_url}/sessions/patient/{patient_id}")
            passed = response.status_code == 200
            patient_sessions = response.json() if passed else None
            self.log_test(
                "Get Patient Sessions", 
                passed, 
                f"Found {patient_sessions.get('total', 0)} sessions for patient" if passed else f"Status: {response.status_code}",
                patient_sessions
            )
        except Exception as e:
            self.log_test("Get Patient Sessions", False, f"Exception: {str(e)}")
        
        # Test updating session
        if self.created_resources["sessions"]:
            session_id = self.created_resources["sessions"][0]
            update_data = {"notes": "Patient appears healthy. Recommended regular exercise."}
            try:
                response = await client.put(f"{self.api_url}/sessions/{session_id}", json=update_data)
                passed = response.status_code == 200
                updated_session = response.json() if passed else None
                self.log_test(
                    "Update Session", 
                    passed, 
                    "Added notes to session" if passed else f"Status: {response.status_code}",
                    updated_session
                )
            except Exception as e:
                self.log_test("Update Session", False, f"Exception: {str(e)}")
    
    async def test_recording_endpoints(self, client: httpx.AsyncClient):
        """Test recording endpoints"""
        if not self.created_resources["sessions"]:
            self.log_test("Start Recording", False, "No sessions available for recording creation")
            return
        
        session_id = self.created_resources["sessions"][0]
        
        # Test starting a recording
        try:
            response = await client.post(f"{self.api_url}/recordings/start", json={"session_id": session_id})
            passed = response.status_code == 201
            if passed:
                created_recording = response.json()
                self.created_resources["recordings"].append(created_recording["id"])
                self.log_test(
                    "Start Recording", 
                    True, 
                    f"Started recording with ID: {created_recording['id']}",
                    created_recording
                )
            else:
                self.log_test(
                    "Start Recording", 
                    False, 
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            self.log_test("Start Recording", False, f"Exception: {str(e)}")
        
        # Test getting a recording
        if self.created_resources["recordings"]:
            recording_id = self.created_resources["recordings"][0]
            try:
                response = await client.get(f"{self.api_url}/recordings/{recording_id}")
                passed = response.status_code == 200
                recording_data = response.json() if passed else None
                self.log_test(
                    "Get Recording", 
                    passed, 
                    f"Retrieved recording with status: {recording_data.get('status', '')}" if passed else f"Status: {response.status_code}",
                    recording_data
                )
            except Exception as e:
                self.log_test("Get Recording", False, f"Exception: {str(e)}")
        
        # Test getting session recordings
        try:
            response = await client.get(f"{self.api_url}/recordings/session/{session_id}")
            passed = response.status_code == 200
            session_recordings = response.json() if passed else None
            self.log_test(
                "Get Session Recordings", 
                passed, 
                f"Found {len(session_recordings) if session_recordings else 0} recordings for session" if passed else f"Status: {response.status_code}",
                session_recordings
            )
        except Exception as e:
            self.log_test("Get Session Recordings", False, f"Exception: {str(e)}")
        
        # Test stopping a recording
        if self.created_resources["recordings"]:
            recording_id = self.created_resources["recordings"][0]
            try:
                response = await client.post(f"{self.api_url}/recordings/stop", json={"recording_id": recording_id})
                passed = response.status_code == 200
                stopped_recording = response.json() if passed else None
                self.log_test(
                    "Stop Recording", 
                    passed, 
                    f"Stopped recording, status: {stopped_recording.get('status', '')}" if passed else f"Status: {response.status_code}",
                    stopped_recording
                )
            except Exception as e:
                self.log_test("Stop Recording", False, f"Exception: {str(e)}")
    
    async def test_analysis_endpoints(self, client: httpx.AsyncClient):
        """Test analysis endpoints"""
        if not self.created_resources["sessions"]:
            self.log_test("Create Analysis", False, "No sessions available for analysis creation")
            return
        
        session_id = self.created_resources["sessions"][0]
        
        # First, we need a recording with a transcript for analysis
        # Since we don't have OpenAI configured, we'll simulate this by creating a mock analysis request
        analysis_data = {
            "session_id": session_id,
            "analysis_type": "general_analysis",
            "include_patient_history": True,
            "custom_prompt": "Analyze this patient consultation for key health insights."
        }
        
        # Test creating an analysis
        try:
            response = await client.post(f"{self.api_url}/analysis/", json=analysis_data)
            # This might fail due to missing transcript, but we test the endpoint
            if response.status_code == 201:
                created_analysis = response.json()
                self.created_resources["analyses"].append(created_analysis["id"])
                self.log_test(
                    "Create Analysis", 
                    True, 
                    f"Created analysis with ID: {created_analysis['id']}",
                    created_analysis
                )
            elif response.status_code == 400:
                # Expected if no transcript available
                self.log_test(
                    "Create Analysis", 
                    True, 
                    "Correctly rejected analysis creation - no transcript available (expected behavior)"
                )
            else:
                self.log_test(
                    "Create Analysis", 
                    False, 
                    f"Unexpected status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            self.log_test("Create Analysis", False, f"Exception: {str(e)}")
        
        # Test getting session analyses
        try:
            response = await client.get(f"{self.api_url}/analysis/session/{session_id}")
            passed = response.status_code == 200
            session_analyses = response.json() if passed else None
            self.log_test(
                "Get Session Analyses", 
                passed, 
                f"Found {session_analyses.get('total', 0)} analyses for session" if passed else f"Status: {response.status_code}",
                session_analyses
            )
        except Exception as e:
            self.log_test("Get Session Analyses", False, f"Exception: {str(e)}")
        
        # Test getting patient analyses
        if self.created_resources["patients"]:
            patient_id = self.created_resources["patients"][0]
            try:
                response = await client.get(f"{self.api_url}/analysis/patient/{patient_id}")
                passed = response.status_code == 200
                patient_analyses = response.json() if passed else None
                self.log_test(
                    "Get Patient Analyses", 
                    passed, 
                    f"Found {patient_analyses.get('total', 0)} analyses for patient" if passed else f"Status: {response.status_code}",
                    patient_analyses
                )
            except Exception as e:
                self.log_test("Get Patient Analyses", False, f"Exception: {str(e)}")
        
        # Test getting an analysis (if we created one)
        if self.created_resources["analyses"]:
            analysis_id = self.created_resources["analyses"][0]
            try:
                response = await client.get(f"{self.api_url}/analysis/{analysis_id}")
                passed = response.status_code == 200
                analysis_data = response.json() if passed else None
                self.log_test(
                    "Get Analysis", 
                    passed, 
                    f"Retrieved analysis with status: {analysis_data.get('status', '')}" if passed else f"Status: {response.status_code}",
                    analysis_data
                )
            except Exception as e:
                self.log_test("Get Analysis", False, f"Exception: {str(e)}")
    
    async def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Horizon 1000 API Test Suite")
        print("=" * 60)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Basic connectivity tests
            print("\n📡 Testing Basic Connectivity...")
            await self.test_health_endpoint(client)
            await self.test_root_endpoint(client)
            
            # Patient endpoints
            print("\n👥 Testing Patient Endpoints...")
            await self.test_patient_endpoints(client)
            
            # Session endpoints
            print("\n🏥 Testing Session Endpoints...")
            await self.test_session_endpoints(client)
            
            # Recording endpoints
            print("\n🎤 Testing Recording Endpoints...")
            await self.test_recording_endpoints(client)
            
            # Analysis endpoints
            print("\n🧠 Testing Analysis Endpoints...")
            await self.test_analysis_endpoints(client)
        
        # Generate summary report
        await self.generate_summary_report()
    
    async def generate_summary_report(self):
        """Generate and display test summary report"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 60)
        
        # Overall statistics
        total = self.test_results["total_tests"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # Test categories breakdown
        categories = {
            "Basic Connectivity": ["Health Check", "Root Endpoint"],
            "Patient Management": ["Create Patient", "Get Patient", "Search Patients", "List Patients", "Update Patient"],
            "Session Management": ["Create Session", "Get Session", "Get Patient Sessions", "Update Session"],
            "Recording Management": ["Start Recording", "Get Recording", "Get Session Recordings", "Stop Recording"],
            "Analysis Management": ["Create Analysis", "Get Session Analyses", "Get Patient Analyses", "Get Analysis"]
        }
        
        print("\n📋 Results by Category:")
        for category, tests in categories.items():
            category_results = [t for t in self.test_results["test_details"] if any(test_name in t["test"] for test_name in tests)]
            if category_results:
                category_passed = sum(1 for t in category_results if t["passed"])
                category_total = len(category_results)
                category_rate = (category_passed / category_total * 100) if category_total > 0 else 0
                print(f"  {category}: {category_passed}/{category_total} ({category_rate:.1f}%)")
        
        # Created resources summary
        print(f"\n🏗️  Resources Created During Testing:")
        print(f"  Patients: {len(self.created_resources['patients'])}")
        print(f"  Sessions: {len(self.created_resources['sessions'])}")
        print(f"  Recordings: {len(self.created_resources['recordings'])}")
        print(f"  Analyses: {len(self.created_resources['analyses'])}")
        
        # Error details
        if self.test_results["errors"]:
            print(f"\n❌ Failed Tests Details:")
            for error in self.test_results["errors"]:
                print(f"  • {error}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if failed == 0:
            print("  🎉 All tests passed! API is functioning correctly.")
        else:
            print("  🔧 Review failed tests and fix issues before deployment.")
            if "OpenAI" in str(self.test_results["errors"]):
                print("  🔑 Configure OpenAI API key for full transcription/analysis functionality.")
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "success_rate": success_rate
            },
            "created_resources": self.created_resources,
            "detailed_results": self.test_results["test_details"]
        }
        
        report_file = Path("api_test_report.json")
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file.absolute()}")

async def main():
    """Main test execution function"""
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/health", timeout=5.0)
            if response.status_code != 200:
                print("❌ Server is not responding properly. Please start the FastAPI server first.")
                print("Run: poetry run uvicorn app.main:app --reload")
                return
    except Exception as e:
        print("❌ Cannot connect to server. Please start the FastAPI server first.")
        print("Run: poetry run uvicorn app.main:app --reload")
        print(f"Error: {e}")
        return
    
    # Run tests
    tester = APITester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())