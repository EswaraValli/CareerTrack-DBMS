-- CareerTrack PMS - Project Specific Tables (from Assignment 1)
-- Placement Management System Database Schema

-- Department table
CREATE TABLE IF NOT EXISTS Department (
    DeptID INTEGER PRIMARY KEY AUTOINCREMENT,
    DeptName VARCHAR(100) NOT NULL,
    HODName VARCHAR(100)
);

-- Student/Member table
CREATE TABLE IF NOT EXISTS Student (
    StudentID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER UNIQUE,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    ContactNumber VARCHAR(15),
    DeptID INTEGER,
    CGPA DECIMAL(3,2),
    GraduationYear INTEGER,
    Image TEXT,
    Age INTEGER,
    IsPlaced BOOLEAN DEFAULT 0,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE SET NULL,
    FOREIGN KEY (DeptID) REFERENCES Department(DeptID) ON DELETE SET NULL
);

-- Company table
CREATE TABLE IF NOT EXISTS Company (
    CompanyID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER UNIQUE,
    CompanyName VARCHAR(200) NOT NULL,
    Website VARCHAR(200),
    Industry VARCHAR(100),
    Location VARCHAR(200),
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE SET NULL
);

-- PlacementDrive table
CREATE TABLE IF NOT EXISTS PlacementDrive (
    DriveID INTEGER PRIMARY KEY AUTOINCREMENT,
    DriveName VARCHAR(200) NOT NULL,
    Year INTEGER NOT NULL,
    StartDate DATE,
    EndDate DATE,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- JobPosting table
CREATE TABLE IF NOT EXISTS JobPosting (
    JobID INTEGER PRIMARY KEY AUTOINCREMENT,
    CompanyID INTEGER NOT NULL,
    DriveID INTEGER,
    RoleTitle VARCHAR(200) NOT NULL,
    Description TEXT,
    Package_LPA DECIMAL(10,2),
    MinCGPA DECIMAL(3,2),
    PostDate DATE DEFAULT (DATE('now')),
    Deadline DATE,
    JobType VARCHAR(50),
    FOREIGN KEY (CompanyID) REFERENCES Company(CompanyID) ON DELETE CASCADE,
    FOREIGN KEY (DriveID) REFERENCES PlacementDrive(DriveID) ON DELETE SET NULL
);

-- Skill table
CREATE TABLE IF NOT EXISTS Skill (
    SkillID INTEGER PRIMARY KEY AUTOINCREMENT,
    SkillName VARCHAR(100) UNIQUE NOT NULL,
    Category VARCHAR(50)
);

-- StudentSkill junction table
CREATE TABLE IF NOT EXISTS StudentSkill (
    StudentID INTEGER NOT NULL,
    SkillID INTEGER NOT NULL,
    ProficiencyLevel VARCHAR(50),
    PRIMARY KEY (StudentID, SkillID),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID) ON DELETE CASCADE,
    FOREIGN KEY (SkillID) REFERENCES Skill(SkillID) ON DELETE CASCADE
);

-- Application table
CREATE TABLE IF NOT EXISTS Application (
    AppID INTEGER PRIMARY KEY AUTOINCREMENT,
    StudentID INTEGER NOT NULL,
    JobID INTEGER NOT NULL,
    ApplyDate DATE DEFAULT (DATE('now')),
    Status VARCHAR(50) DEFAULT 'Applied' CHECK(Status IN ('Applied', 'Shortlisted', 'Rejected', 'Selected', 'Withdrawn')),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID) ON DELETE CASCADE,
    FOREIGN KEY (JobID) REFERENCES JobPosting(JobID) ON DELETE CASCADE,
    UNIQUE(StudentID, JobID)
);

-- Recruiter table
CREATE TABLE IF NOT EXISTS Recruiter (
    RecruiterID INTEGER PRIMARY KEY AUTOINCREMENT,
    CompanyID INTEGER NOT NULL,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    Phone VARCHAR(15),
    FOREIGN KEY (CompanyID) REFERENCES Company(CompanyID) ON DELETE CASCADE
);

-- InterviewRound table
CREATE TABLE IF NOT EXISTS InterviewRound (
    RoundID INTEGER PRIMARY KEY AUTOINCREMENT,
    JobID INTEGER NOT NULL,
    RoundType VARCHAR(50),
    RoundNumber INTEGER,
    FOREIGN KEY (JobID) REFERENCES JobPosting(JobID) ON DELETE CASCADE
);

-- InterviewSchedule table
CREATE TABLE IF NOT EXISTS InterviewSchedule (
    ScheduleID INTEGER PRIMARY KEY AUTOINCREMENT,
    RoundID INTEGER NOT NULL,
    RecruiterID INTEGER,
    InterviewDate DATE,
    MeetingLink TEXT,
    FOREIGN KEY (RoundID) REFERENCES InterviewRound(RoundID) ON DELETE CASCADE,
    FOREIGN KEY (RecruiterID) REFERENCES Recruiter(RecruiterID) ON DELETE SET NULL
);

-- PlacementOffer table
CREATE TABLE IF NOT EXISTS PlacementOffer (
    OfferID INTEGER PRIMARY KEY AUTOINCREMENT,
    StudentID INTEGER NOT NULL,
    JobID INTEGER NOT NULL,
    CompanyID INTEGER NOT NULL,
    OfferDate DATE DEFAULT (DATE('now')),
    FinalPackage DECIMAL(10,2),
    AcceptanceStatus VARCHAR(50) DEFAULT 'Pending' CHECK(AcceptanceStatus IN ('Pending', 'Accepted', 'Rejected')),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID) ON DELETE CASCADE,
    FOREIGN KEY (JobID) REFERENCES JobPosting(JobID) ON DELETE CASCADE,
    FOREIGN KEY (CompanyID) REFERENCES Company(CompanyID) ON DELETE CASCADE
);

-- Sample Data Insertion

-- Insert Departments
INSERT OR IGNORE INTO Department (DeptID, DeptName, HODName) VALUES 
(1, 'Computer Science and Engineering', 'Dr. Rajesh Kumar'),
(2, 'Electrical Engineering', 'Dr. Priya Sharma'),
(3, 'Mechanical Engineering', 'Dr. Amit Patel'),
(4, 'Civil Engineering', 'Dr. Sneha Verma');

-- Insert Skills
INSERT OR IGNORE INTO Skill (SkillID, SkillName, Category) VALUES 
(1, 'Python', 'Programming'),
(2, 'Java', 'Programming'),
(3, 'Machine Learning', 'Technical'),
(4, 'Data Structures', 'Technical'),
(5, 'Web Development', 'Technical'),
(6, 'Communication', 'Soft Skill'),
(7, 'Leadership', 'Soft Skill'),
(8, 'SQL', 'Database'),
(9, 'React', 'Framework'),
(10, 'Cloud Computing', 'Technical');

-- Insert Sample Students (linked to Users table)
INSERT OR IGNORE INTO Student (StudentID, Name, Email, ContactNumber, DeptID, CGPA, GraduationYear, Age, IsPlaced) VALUES 
(1, 'Divyansh Saini', 'divyansh@student.iitgn.ac.in', '9876543210', 1, 8.5, 2026, 21, 0),
(2, 'Pramith Joy', 'pramith@student.iitgn.ac.in', '9876543211', 1, 8.8, 2026, 22, 0),
(3, 'Garv Singhal', 'garv@student.iitgn.ac.in', '9876543212', 1, 9.2, 2026, 21, 0),
(4, 'Bhavitha Somireddy', 'bhavitha@student.iitgn.ac.in', '9876543213', 1, 8.7, 2026, 21, 0),
(5, 'Killada Eswara Valli', 'eswara@student.iitgn.ac.in', '9876543214', 1, 8.9, 2026, 22, 0),
(6, 'Rahul Mehta', 'rahul@student.iitgn.ac.in', '9876543215', 2, 8.3, 2026, 22, 0),
(7, 'Sneha Reddy', 'sneha@student.iitgn.ac.in', '9876543216', 1, 9.0, 2026, 21, 0),
(8, 'Arjun Singh', 'arjun@student.iitgn.ac.in', '9876543217', 3, 7.9, 2026, 23, 0);

-- Insert Companies
INSERT OR IGNORE INTO Company (CompanyID, CompanyName, Website, Industry, Location) VALUES 
(1, 'Google India', 'https://www.google.com', 'Technology', 'Bangalore'),
(2, 'Microsoft', 'https://www.microsoft.com', 'Technology', 'Hyderabad'),
(3, 'Amazon', 'https://www.amazon.com', 'E-commerce', 'Bangalore'),
(4, 'TCS', 'https://www.tcs.com', 'IT Services', 'Mumbai'),
(5, 'Infosys', 'https://www.infosys.com', 'IT Services', 'Pune'),
(6, 'Flipkart', 'https://www.flipkart.com', 'E-commerce', 'Bangalore');

-- Insert Placement Drives
INSERT OR IGNORE INTO PlacementDrive (DriveID, DriveName, Year, StartDate, EndDate) VALUES 
(1, 'Campus Placement 2025-26', 2026, '2025-09-01', '2026-04-30'),
(2, 'Off-Campus Drive 2025', 2025, '2025-07-01', '2025-08-31');

-- Insert Job Postings
INSERT OR IGNORE INTO JobPosting (JobID, CompanyID, DriveID, RoleTitle, Description, Package_LPA, MinCGPA, PostDate, Deadline, JobType) VALUES 
(1, 1, 1, 'Software Engineer', 'Full-time software development role', 18.5, 7.5, '2025-09-15', '2025-10-15', 'Full-time'),
(2, 2, 1, 'Data Scientist', 'Work on AI/ML projects', 20.0, 8.0, '2025-09-20', '2025-10-20', 'Full-time'),
(3, 3, 1, 'SDE Intern', 'Summer internship opportunity', 1.2, 7.0, '2025-09-10', '2025-10-10', 'Internship'),
(4, 4, 1, 'System Engineer', 'Entry-level IT role', 3.5, 6.5, '2025-09-25', '2025-11-01', 'Full-time'),
(5, 5, 1, 'Software Developer', 'Development and testing role', 4.0, 7.0, '2025-10-01', '2025-11-05', 'Full-time'),
(6, 6, 1, 'Product Manager Intern', 'Product management internship', 0.8, 7.5, '2025-10-05', '2025-11-10', 'Internship');

-- Insert Student Skills
INSERT OR IGNORE INTO StudentSkill (StudentID, SkillID, ProficiencyLevel) VALUES 
(1, 1, 'Expert'),
(1, 4, 'Advanced'),
(1, 8, 'Intermediate'),
(2, 2, 'Expert'),
(2, 3, 'Advanced'),
(3, 1, 'Expert'),
(3, 9, 'Advanced'),
(3, 5, 'Expert'),
(4, 1, 'Advanced'),
(4, 4, 'Expert'),
(5, 3, 'Expert'),
(5, 10, 'Advanced');

-- Insert Applications
INSERT OR IGNORE INTO Application (AppID, StudentID, JobID, ApplyDate, Status) VALUES 
(1, 1, 1, '2025-09-16', 'Shortlisted'),
(2, 2, 2, '2025-09-21', 'Applied'),
(3, 3, 1, '2025-09-17', 'Selected'),
(4, 3, 3, '2025-09-12', 'Applied'),
(5, 4, 1, '2025-09-18', 'Applied'),
(6, 5, 2, '2025-09-22', 'Shortlisted'),
(7, 1, 3, '2025-09-11', 'Applied'),
(8, 2, 4, '2025-09-26', 'Applied');

-- Insert Recruiters
INSERT OR IGNORE INTO Recruiter (RecruiterID, CompanyID, Name, Email, Phone) VALUES 
(1, 1, 'Amit Shah', 'amit.shah@google.com', '9123456789'),
(2, 2, 'Priya Nair', 'priya.nair@microsoft.com', '9123456790'),
(3, 3, 'Rohan Gupta', 'rohan.gupta@amazon.com', '9123456791'),
(4, 4, 'Kavita Reddy', 'kavita.reddy@tcs.com', '9123456792');

-- Insert Interview Rounds
INSERT OR IGNORE INTO InterviewRound (RoundID, JobID, RoundType, RoundNumber) VALUES 
(1, 1, 'Coding Round', 1),
(2, 1, 'Technical Interview', 2),
(3, 1, 'HR Round', 3),
(4, 2, 'Aptitude Test', 1),
(5, 2, 'Technical Interview', 2);

-- Insert Interview Schedules
INSERT OR IGNORE INTO InterviewSchedule (ScheduleID, RoundID, RecruiterID, InterviewDate, MeetingLink) VALUES 
(1, 2, 1, '2025-10-20', 'https://meet.google.com/abc-defg-hij'),
(2, 3, 1, '2025-10-25', 'https://meet.google.com/xyz-pqrs-tuv'),
(3, 5, 2, '2025-10-22', 'https://teams.microsoft.com/meet/123');

-- Insert Placement Offers
INSERT OR IGNORE INTO PlacementOffer (OfferID, StudentID, JobID, CompanyID, OfferDate, FinalPackage, AcceptanceStatus) VALUES 
(1, 3, 1, 1, '2025-10-30', 18.5, 'Accepted');
