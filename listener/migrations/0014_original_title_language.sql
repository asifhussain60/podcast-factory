-- `title_arabic` predates books whose original title is Urdu. Keep the legacy
-- text column for migration compatibility, and record the BCP-47 language so
-- each script can select the correct face and semantic `lang` attribute.
ALTER TABLE unit_detail ADD COLUMN title_language TEXT
  CHECK (title_language IS NULL OR title_language IN ('ar', 'ur', 'zh'));
