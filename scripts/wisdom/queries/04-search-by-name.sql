-- KSessions: search sessions by name or content keyword
-- Run via VS Code MSSQL extension → AHHOME profile → KSESSIONS_DEV

USE KSESSIONS_DEV;

-- ── Change this value ──────────────────────────────────────────────────────────
DECLARE @Keyword NVARCHAR(200) = N'Isbat';   -- partial name match (case-insensitive)
-- ───────────────────────────────────────────────────────────────────────────────

SELECT
    s.SessionID,
    g.GroupName,
    c.CategoryName,
    s.Sequence,
    s.SessionName,
    CASE WHEN t.Transcript IS NOT NULL THEN 'yes' ELSE 'no' END AS HasTranscript
FROM dbo.Sessions s
JOIN dbo.Groups g     ON g.GroupID    = s.GroupID
JOIN dbo.Categories c ON c.CategoryID = s.CategoryID
LEFT JOIN dbo.SessionTranscripts t ON t.SessionID = s.SessionID
WHERE s.SessionName LIKE N'%' + @Keyword + N'%'
ORDER BY s.GroupID, s.Sequence;
