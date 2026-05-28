-- KASHKOLE database inventory
-- Server: 192.168.1.158  |  DB: KASHKOLE  |  Profile: AHHOME
-- Kashkole is the master Urdu-unicode knowledge repository: Binders > Chapters > Topics > Content

USE KASHKOLE;
GO

-- Row counts across all key content tables
SELECT 'Binders'           AS TableName, COUNT(*) AS RowCount FROM Binders
UNION ALL
SELECT 'Chapters',                        COUNT(*) FROM Chapters
UNION ALL
SELECT 'Topics',                          COUNT(*) FROM Topics
UNION ALL
SELECT 'Topics (English)',                COUNT(*) FROM Topics WHERE IsEnglish = 1
UNION ALL
SELECT 'Topics (HasSimpleVersion)',       COUNT(*) FROM Topics WHERE HasSimpleVersion = 1
UNION ALL
SELECT 'TopicDataUnicode (has content)',  COUNT(*) FROM TopicDataUnicode WHERE LEN(TopicUnicode) > 0
UNION ALL
SELECT 'TopicAyats (Quran cross-refs)',   COUNT(*) FROM TopicAyats
UNION ALL
SELECT 'TopicFlashcards',                 COUNT(*) FROM TopicFlashcards
UNION ALL
SELECT 'Glossary',                        COUNT(*) FROM Glossary
UNION ALL
SELECT 'DeeniTermGroups',                 COUNT(*) FROM DeeniTermGroup
ORDER BY TableName;

-- Binder list (book-level containers)
SELECT  b.BinderID
      , b.BinderName
      , b.BinderDescription
      , COUNT(bc.ChapterID) AS ChapterCount
FROM    Binders       b
LEFT JOIN BinderChapters bc ON bc.BinderID = b.BinderID
GROUP BY b.BinderID, b.BinderName, b.BinderDescription
ORDER BY b.BinderID;
