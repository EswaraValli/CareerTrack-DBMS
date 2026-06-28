-- CareerTrack PMS - Core System Tables
-- These tables handle user authentication, roles, and system-wide data

-- Users table for authentication
CREATE TABLE IF NOT EXISTS Users (
    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
    Username VARCHAR(50) UNIQUE NOT NULL,
    PasswordHash TEXT NOT NULL,
    Role VARCHAR(20) NOT NULL CHECK(Role IN ('Admin', 'Student', 'Company', 'PlacementOfficer')),
    Email VARCHAR(100) UNIQUE NOT NULL,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    LastLogin DATETIME,
    IsActive BOOLEAN DEFAULT 1
);

-- Sessions table for JWT-like session management
CREATE TABLE IF NOT EXISTS Sessions (
    SessionID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER NOT NULL,
    SessionToken TEXT UNIQUE NOT NULL,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    ExpiresAt DATETIME NOT NULL,
    IsValid BOOLEAN DEFAULT 1,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

-- Audit log table for tracking all database operations
CREATE TABLE IF NOT EXISTS AuditLog (
    LogID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER,
    Username VARCHAR(50),
    Action VARCHAR(50) NOT NULL,
    TableName VARCHAR(50),
    RecordID INTEGER,
    OldValue TEXT,
    NewValue TEXT,
    IPAddress VARCHAR(45),
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    IsAuthorized BOOLEAN DEFAULT 1,
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE SET NULL
);

-- System Settings table
CREATE TABLE IF NOT EXISTS SystemSettings (
    SettingID INTEGER PRIMARY KEY AUTOINCREMENT,
    SettingKey VARCHAR(100) UNIQUE NOT NULL,
    SettingValue TEXT,
    Description TEXT,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin user (password: admin123)
-- Password hash: hashlib.sha256(('admin123' + 'careertrack_salt_2026').encode()).hexdigest()
INSERT OR IGNORE INTO Users (Username, PasswordHash, Role, Email) VALUES 
('admin', '741a92d325a5bf156449f9af4245500a01397175a284ec326da7d045bfe3c309', 'Admin', 'admin@careertrack.com');

-- Insert default placement officer (password: officer123)
-- Password hash: hashlib.sha256(('officer123' + 'careertrack_salt_2026').encode()).hexdigest()
INSERT OR IGNORE INTO Users (Username, PasswordHash, Role, Email) VALUES 
('officer', '7bf6b450250c1a208bd5c95f4db383d8bc1d490e0205d75fd088a746b54a61a1', 'PlacementOfficer', 'officer@careertrack.com');

-- Insert system settings
INSERT OR IGNORE INTO SystemSettings (SettingKey, SettingValue, Description) VALUES 
('session_timeout_hours', '24', 'Session timeout duration in hours'),
('max_login_attempts', '5', 'Maximum failed login attempts before lockout'),
('enable_audit_logging', 'true', 'Enable/disable audit logging');
