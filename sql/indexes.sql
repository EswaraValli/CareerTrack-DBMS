-- CareerTrack PMS - Database Indexes for Query Optimization
-- These indexes are designed to optimize the most frequently accessed queries in the API

-- ============================================
-- CORE TABLES INDEXES
-- ============================================

-- Index on Username for login queries
CREATE INDEX IF NOT EXISTS idx_users_username ON Users(Username);

-- Index on Email for user lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON Users(Email);

-- Index on Role for role-based filtering
CREATE INDEX IF NOT EXISTS idx_users_role ON Users(Role);

-- Index on SessionToken for session validation
CREATE INDEX IF NOT EXISTS idx_sessions_token ON Sessions(SessionToken);

-- Composite index for active sessions by user
CREATE INDEX IF NOT EXISTS idx_sessions_user_valid ON Sessions(UserID, IsValid, ExpiresAt);

-- Index on AuditLog for filtering by user and timestamp
CREATE INDEX IF NOT EXISTS idx_audit_user_time ON AuditLog(UserID, Timestamp);

-- Index on AuditLog for filtering by table and action
CREATE INDEX IF NOT EXISTS idx_audit_table_action ON AuditLog(TableName, Action);

-- ============================================
-- PROJECT-SPECIFIC TABLES INDEXES
-- ============================================

-- Student table indexes
CREATE INDEX IF NOT EXISTS idx_student_userid ON Student(UserID);
CREATE INDEX IF NOT EXISTS idx_student_email ON Student(Email);
CREATE INDEX IF NOT EXISTS idx_student_dept ON Student(DeptID);
CREATE INDEX IF NOT EXISTS idx_student_cgpa ON Student(CGPA);
CREATE INDEX IF NOT EXISTS idx_student_year ON Student(GraduationYear);
CREATE INDEX IF NOT EXISTS idx_student_placed ON Student(IsPlaced);

-- Composite index for eligibility checking (frequently used in job applications)
CREATE INDEX IF NOT EXISTS idx_student_cgpa_year_placed ON Student(CGPA, GraduationYear, IsPlaced);

-- Company table indexes
CREATE INDEX IF NOT EXISTS idx_company_userid ON Company(UserID);
CREATE INDEX IF NOT EXISTS idx_company_name ON Company(CompanyName);
CREATE INDEX IF NOT EXISTS idx_company_industry ON Company(Industry);

-- JobPosting table indexes
CREATE INDEX IF NOT EXISTS idx_job_company ON JobPosting(CompanyID);
CREATE INDEX IF NOT EXISTS idx_job_drive ON JobPosting(DriveID);
CREATE INDEX IF NOT EXISTS idx_job_mincgpa ON JobPosting(MinCGPA);
CREATE INDEX IF NOT EXISTS idx_job_deadline ON JobPosting(Deadline);

-- Composite index for active job listings with eligibility
CREATE INDEX IF NOT EXISTS idx_job_active_eligible ON JobPosting(Deadline, MinCGPA, JobType);

-- Application table indexes (most frequently queried)
CREATE INDEX IF NOT EXISTS idx_application_student ON Application(StudentID);
CREATE INDEX IF NOT EXISTS idx_application_job ON Application(JobID);
CREATE INDEX IF NOT EXISTS idx_application_status ON Application(Status);

-- Composite index for student's application history
CREATE INDEX IF NOT EXISTS idx_application_student_status ON Application(StudentID, Status);

-- Composite index for job applicants
CREATE INDEX IF NOT EXISTS idx_application_job_status ON Application(JobID, Status);

-- PlacementOffer table indexes
CREATE INDEX IF NOT EXISTS idx_offer_student ON PlacementOffer(StudentID);
CREATE INDEX IF NOT EXISTS idx_offer_job ON PlacementOffer(JobID);
CREATE INDEX IF NOT EXISTS idx_offer_company ON PlacementOffer(CompanyID);
CREATE INDEX IF NOT EXISTS idx_offer_status ON PlacementOffer(AcceptanceStatus);

-- Composite index for placement tracking
CREATE INDEX IF NOT EXISTS idx_offer_student_status ON PlacementOffer(StudentID, AcceptanceStatus);

-- Skill and StudentSkill indexes
CREATE INDEX IF NOT EXISTS idx_skill_name ON Skill(SkillName);
CREATE INDEX IF NOT EXISTS idx_skill_category ON Skill(Category);
CREATE INDEX IF NOT EXISTS idx_studentskill_student ON StudentSkill(StudentID);
CREATE INDEX IF NOT EXISTS idx_studentskill_skill ON StudentSkill(SkillID);

-- Recruiter indexes
CREATE INDEX IF NOT EXISTS idx_recruiter_company ON Recruiter(CompanyID);
CREATE INDEX IF NOT EXISTS idx_recruiter_email ON Recruiter(Email);

-- InterviewRound indexes
CREATE INDEX IF NOT EXISTS idx_round_job ON InterviewRound(JobID);

-- InterviewSchedule indexes
CREATE INDEX IF NOT EXISTS idx_schedule_round ON InterviewSchedule(RoundID);
CREATE INDEX IF NOT EXISTS idx_schedule_recruiter ON InterviewSchedule(RecruiterID);
CREATE INDEX IF NOT EXISTS idx_schedule_date ON InterviewSchedule(InterviewDate);

-- PlacementDrive indexes
CREATE INDEX IF NOT EXISTS idx_drive_year ON PlacementDrive(Year);
CREATE INDEX IF NOT EXISTS idx_drive_dates ON PlacementDrive(StartDate, EndDate);

-- Department indexes
CREATE INDEX IF NOT EXISTS idx_dept_name ON Department(DeptName);

-- ============================================
-- PERFORMANCE NOTES
-- ============================================
-- These indexes are optimized for:
-- 1. Fast user authentication and session validation
-- 2. Quick student eligibility checks (CGPA-based filtering)
-- 3. Efficient job application tracking
-- 4. Rapid placement offer queries
-- 5. Audit log searches by user and time
-- 6. Member portfolio retrieval
-- 
-- Use EXPLAIN QUERY PLAN to verify index usage in your queries
-- Example: EXPLAIN QUERY PLAN SELECT * FROM Student WHERE CGPA >= 7.5;
