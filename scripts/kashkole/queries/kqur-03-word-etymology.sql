-- KQUR: Arabic root + derivative etymology lookup
-- Server: 192.168.1.158  |  DB: KQUR  |  Profile: AHHOME
-- Returns: root meaning, all derivative forms, grammar tags, definitions

USE KQUR;
GO

-- ---- Option A: search by English keyword in root meaning ----
DECLARE @EnglishKeyword NVARCHAR(100) = 'wisdom'; -- change

SELECT  r.RootID
      , r.RootWord
      , r.RootTransliteration
      , r.MeaningEnglish       AS RootMeaning
      , r.MeaningArabic        AS RootMeaningArabic
      , d.Derivative
      , d.Transliteration      AS DerivativeTranslit
      , d.MeaningEnglish       AS DerivativeMeaning
      , d.Grammar
      , d.Definition
FROM    Roots      r
JOIN    Derivatives d ON d.RootID = r.RootID
WHERE   r.MeaningEnglish LIKE '%' + @EnglishKeyword + '%'
   OR   d.MeaningEnglish LIKE '%' + @EnglishKeyword + '%'
ORDER BY r.RootTransliteration, d.SortOrder;

-- ---- Option B: look up a specific Arabic root word directly ----
-- Uncomment and adjust:
-- DECLARE @ArabicRoot NVARCHAR(50) = N'حكم';
-- SELECT r.*, d.*
-- FROM   Roots r
-- LEFT JOIN Derivatives d ON d.RootID = r.RootID
-- WHERE  r.RootWord = @ArabicRoot
-- ORDER BY d.SortOrder;
