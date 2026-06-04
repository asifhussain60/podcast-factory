-- KSessions: inventory of groups and session counts
-- Run via VS Code MSSQL extension → AHHOME profile → KSESSIONS_DEV

USE KSESSIONS_DEV;

-- All groups with session counts
SELECT
    g.GroupID,
    g.GroupName,
    COUNT(s.SessionID) AS SessionCount
FROM dbo.Groups g
LEFT JOIN dbo.Sessions s ON s.GroupID = g.GroupID
GROUP BY g.GroupID, g.GroupName
ORDER BY g.GroupID;

-- All categories under each group
SELECT
    c.CategoryID,
    c.CategoryName,
    c.GroupID,
    g.GroupName,
    COUNT(s.SessionID) AS SessionCount
FROM dbo.Categories c
JOIN dbo.Groups g ON g.GroupID = c.GroupID
LEFT JOIN dbo.Sessions s ON s.CategoryID = c.CategoryID
GROUP BY c.CategoryID, c.CategoryName, c.GroupID, g.GroupName
ORDER BY c.GroupID, c.CategoryID;
