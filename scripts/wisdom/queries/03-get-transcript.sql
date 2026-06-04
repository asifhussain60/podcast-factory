-- KSessions: retrieve plain-readable transcript for a single session
-- Edit :SessionID below and run
-- Run via VS Code MSSQL extension → AHHOME profile → KSESSIONS_DEV

USE KSESSIONS_DEV;

-- ── Change this value ──────────────────────────────────────────────────────────
DECLARE @TargetSessionID INT = 2346;   -- e.g. 2346 = "Necessity Of Imam" (Isbat al-Imamah)
-- ───────────────────────────────────────────────────────────────────────────────

SELECT
    s.SessionID,
    g.GroupName,
    c.CategoryName,
    s.SessionName,
    t.Transcript          -- full HTML; paste into browser or strip tags for plain text
FROM dbo.Sessions s
JOIN dbo.Groups g           ON g.GroupID    = s.GroupID
JOIN dbo.Categories c       ON c.CategoryID = s.CategoryID
LEFT JOIN dbo.SessionTranscripts t ON t.SessionID = s.SessionID
WHERE s.SessionID = @TargetSessionID;
