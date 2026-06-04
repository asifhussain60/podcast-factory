-- KQUR database inventory
-- Server: 192.168.1.158  |  DB: KQUR  |  Profile: AHHOME
-- Run this first to understand what's in the database.

USE KQUR;
GO

SELECT 'Surahs'         AS TableName, COUNT(*) AS RowCount FROM QuranSurahs
UNION ALL
SELECT 'Ayats',                        COUNT(*) FROM QuranAyats
UNION ALL
SELECT 'Roots',                        COUNT(*) FROM Roots
UNION ALL
SELECT 'Derivatives',                  COUNT(*) FROM Derivatives
UNION ALL
SELECT 'Hadith',                       COUNT(*) FROM Ahadees
UNION ALL
SELECT 'HadithCategories',             COUNT(*) FROM AhadeesSubjectCategories
UNION ALL
SELECT 'Narrators',                    COUNT(*) FROM Narrators
ORDER BY TableName;

-- Surah list (quick reference)
SELECT  SurahID
      , SurahNumber
      , SurahName
      , SurahEnglishName
      , SurahMeaning
      , TotalAyats
FROM    QuranSurahs
ORDER BY SurahNumber;
