-- KQUR: Keyword search across Quran translations + surah names
-- Server: 192.168.1.158  |  DB: KQUR  |  Profile: AHHOME
-- Useful for thematic retrieval during authoring (e.g. find all verses about divine light / tawakkul / aql)

USE KQUR;
GO

DECLARE @Keyword NVARCHAR(200) = 'light'; -- change: English keyword

SELECT  a.SurahNumber
      , s.SurahEnglishName
      , a.AyatNumber
      , a.AyatUNICODE          AS ArabicText
      , a.AyatTranslation      AS TranslationPickthall
      , a.Translation_Asad     AS TranslationAsad
      , a.Phonetic
FROM    QuranAyats  a
JOIN    QuranSurahs s ON s.SurahNumber = a.SurahNumber
WHERE   a.AyatTranslation  LIKE '%' + @Keyword + '%'
   OR   a.Translation_Asad LIKE '%' + @Keyword + '%'
ORDER BY a.SurahNumber, a.AyatNumber;
