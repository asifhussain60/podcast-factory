-- KSessions: list all sessions in the three style-corpus target groups
-- Groups: 3 = Wise Reminder, 17 = Ikhwan As-Safa, 18 = Asaas Al-Taveel
-- Run via VS Code MSSQL extension → AHHOME profile → KSESSIONS_DEV

USE KSESSIONS_DEV;

SELECT
    s.SessionID,
    g.GroupName,
    c.CategoryName,
    s.Sequence,
    s.SessionName,
    CASE
        WHEN t.Transcript IS NULL          THEN 'no-transcript'
        WHEN LEN(t.Transcript) < 200       THEN 'stub'
        ELSE 'has-content (' + CAST(LEN(t.Transcript) AS VARCHAR) + ' chars)'
    END AS TranscriptStatus
FROM dbo.Sessions s
JOIN dbo.Groups g     ON g.GroupID    = s.GroupID
JOIN dbo.Categories c ON c.CategoryID = s.CategoryID
LEFT JOIN dbo.SessionTranscripts t ON t.SessionID = s.SessionID
WHERE s.GroupID IN (3, 17, 18)
  -- Ikhwan: arithmetic category only (Cat 51)
  AND NOT (s.GroupID = 17 AND s.CategoryID != 51)
ORDER BY s.GroupID, s.Sequence;
