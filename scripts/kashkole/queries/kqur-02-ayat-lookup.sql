-- KQUR: Quran verse lookup by surah + ayat number
-- Server: 192.168.1.158  |  DB: KQUR  |  Profile: AHHOME
-- Returns: Arabic unicode, English translation (Pickthall + Asad), phonetic, Urdu translation

USE KQUR;
GO

DECLARE @SurahNumber  INT = 2;   -- change: surah number 1-114
DECLARE @AyatNumber   INT = 255; -- change: ayat number within that surah (0 = whole surah)

SELECT  a.AyatID
      , a.SurahNumber
      , a.AyatNumber
      , s.SurahEnglishName
      , a.AyatUNICODE           AS ArabicText
      , a.AyatTranslation       AS TranslationPickthall
      , a.Translation_Asad      AS TranslationAsad
      , a.Phonetic
      , a.UrduTranslation
      , a.IsSahihTranslation
FROM    QuranAyats  a
JOIN    QuranSurahs s ON s.SurahNumber = a.SurahNumber
WHERE   a.SurahNumber = @SurahNumber
  AND  (@AyatNumber = 0 OR a.AyatNumber = @AyatNumber)
ORDER BY a.AyatNumber;
