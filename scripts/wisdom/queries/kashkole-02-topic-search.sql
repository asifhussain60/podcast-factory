-- KASHKOLE: Search topics by keyword (name or English name)
-- Server: 192.168.1.158  |  DB: KASHKOLE  |  Profile: AHHOME
-- Returns: topic name, English name, type, and a preview of its Unicode content

USE KASHKOLE;
GO

DECLARE @Keyword NVARCHAR(200) = 'aql'; -- change: English keyword to search topic names

SELECT  t.TopicID
      , t.TopicName
      , t.TopicNameEnglish
      , t.TopicTypeID
      , t.IsEnglish
      , t.IsArabic
      , t.HasSimpleVersion
      , t.ViewCount
      , LEFT(u.TopicUnicode, 800)    AS ContentPreview
FROM    Topics            t
LEFT JOIN TopicDataUnicode u ON u.TopicID = t.TopicID
WHERE   t.TopicNameEnglish LIKE '%' + @Keyword + '%'
   OR   t.TopicName        LIKE '%' + @Keyword + '%'
ORDER BY t.ViewCount DESC, t.TopicID;
