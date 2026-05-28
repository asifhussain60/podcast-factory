-- KASHKOLE: Get full content for a specific topic
-- Server: 192.168.1.158  |  DB: KASHKOLE  |  Profile: AHHOME
-- Returns: topic metadata + full Unicode text + linked Quran ayats + glossary terms

USE KASHKOLE;
GO

DECLARE @TargetTopicID INT = 1; -- change: TopicID from kashkole-02-topic-search

-- Full topic content
SELECT  t.TopicID
      , t.TopicName
      , t.TopicNameEnglish
      , t.TopicDescription
      , t.LastUpdated
      , u.TopicUnicode           AS FullContent
      , u.TopicUnicodeStripped   AS PlainTextContent
FROM    Topics            t
LEFT JOIN TopicDataUnicode u ON u.TopicID = t.TopicID
WHERE   t.TopicID = @TargetTopicID;

-- Quran cross-references linked to this topic
SELECT  ta.TopicAyatID
      , ta.SurahNumber
      , ta.AyatNumber
      , ta.AyatText
FROM    TopicAyats ta
WHERE   ta.TopicID = @TargetTopicID
ORDER BY ta.SurahNumber, ta.AyatNumber;

-- Glossary terms linked to this topic
SELECT  tg.TopicGlossaryID
      , g.Term
      , g.Definition
FROM    TopicGlossaries tg
JOIN    Glossary         g  ON g.GlossaryID = tg.GlossaryID
WHERE   tg.TopicID = @TargetTopicID;
