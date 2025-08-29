# Next Development Tasks

## Patient Management Enhancements

### National ID (NIDA) Integration
- [ ] Add National ID field to patient registration
- [ ] Implement NIDA validation API integration
- [ ] Create "Validate NID & Insurance" button functionality
- [ ] Auto-populate patient details from NIDA lookup

### Insurance Management
- [ ] Add insurance status field (covered/not covered)
- [ ] Add insurance coverage details
- [ ] Set default insurance provider to CBHI/RSSB
- [ ] Integrate insurance validation with NID lookup
- [ ] Display insurance status in patient profile

### Patient Data Model Updates
- [ ] Use patient UUID as Medical Record Number (MRN)
- [ ] Add relationship field for emergency contact
- [ ] Update database schema for new fields
- [ ] Create migration scripts

## Session & Consultation Improvements

### Visit Type Management
- [ ] Create visit type enum/dropdown
- [ ] Add visit type options (consultation, follow-up, emergency, etc.)
- [ ] Update session creation to include visit type
- [ ] Filter sessions by visit type

### Language Support
- [ ] Add language specification for sessions
- [ ] Support multiple languages for transcription
- [ ] Update UI to show session language
- [ ] Configure Whisper/AssemblyAI for different languages

## User Management & Authentication

### Account Management System
- [ ] Implement admin user role
- [ ] Create practitioner registration (admin-only)
- [ ] Build practitioner login system
- [ ] Session-based authentication for practitioners
- [ ] Role-based access control (admin vs practitioner)

### Practitioner Dashboard
- [ ] Practitioner-specific session management
- [ ] Only show sessions for logged-in practitioner
- [ ] Practitioner profile management

## UI/UX Improvements

### Health Facility Display
- [ ] Show health facility name prominently
- [ ] Display facility next to patient names/details
- [ ] Add facility information to session headers
- [ ] Configure facility details in settings

### Analysis System Cleanup
- [ ] Remove analysis type selection (simplify workflow)
- [ ] Streamline analysis creation process
- [ ] Focus on single analysis type per session

## Patient Timeline Enhancement

### Improved Data Aggregation
- [ ] Add meaningful health metrics
- [ ] Track consultation frequency and patterns
- [ ] Monitor patient compliance and follow-up rates
- [ ] Calculate health trend indicators

### Valuable Metrics Implementation
- [ ] Patient visit frequency analysis
- [ ] Treatment adherence tracking
- [ ] Health outcome measurements
- [ ] Risk factor identification
- [ ] Care quality indicators

### Timeline Visualization
- [ ] Enhanced chart types for health data
- [ ] Interactive timeline with drill-down capabilities
- [ ] Trend analysis with predictive insights
- [ ] Comparative health metrics over time

## Audio & Recording Recovery

### Post-LiveKit Recording
- [ ] Implement LiveKit room recording
- [ ] Process recorded files for transcription
- [ ] Add speaker diarization to recorded sessions
- [ ] Maintain file-based transcript storage
- [ ] Integrate recorded transcripts with real-time data

## Technical Debt & Infrastructure

### Database Improvements
- [ ] Update all models for new patient fields
- [ ] Optimize queries for new relationships
- [ ] Add proper indexing for new fields
- [ ] Data validation for insurance and NID fields

### API Updates
- [ ] Update patient API for new fields
- [ ] Add insurance validation endpoints
- [ ] NIDA integration API endpoints
- [ ] Enhanced search with new fields

### Frontend Updates
- [ ] Update patient forms for new fields
- [ ] Insurance status display components
- [ ] NID validation UI feedback
- [ ] Facility display components

---

## Priority Order

1. **High Priority** (Core functionality)
   - NIDA integration with insurance validation
   - Account management system
   - Visit type dropdown
   - Health facility display

2. **Medium Priority** (Enhanced features)
   - Patient timeline improvements
   - Language support for sessions
   - Audio recording recovery

3. **Low Priority** (Nice to have)
   - Advanced analytics
   - UI polish
   - Performance optimizations

---

*Last updated: August 27, 2025*