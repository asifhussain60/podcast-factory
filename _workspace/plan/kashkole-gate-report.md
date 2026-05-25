# KAHSKOLE Pipeline — GATE Report
*Generated: 2026-05-25 14:17 UTC*

## At a Glance

| Metric | Value |
|---|---|
| Total chapters | 122 |
| Challenged (Phase 3 complete) | 62 |
| Adapted (Phase 2 complete) | 37 |
| Translated only (Phase 1) | 23 |
| GATE ready | ❌ NOT YET |

## Challenge Results

| Verdict | Count |
|---|---|
| PASS | 8 |
| WARN | 37 |
| FAIL | 17 |

## Cost Summary

| Phase | Cost (USD) |
|---|---|
| Phase 1 — Azure translate | $38.37 |
| Phase 2 — Adaptation (Anthropic) | $5.30 |
| Phase 3 — Challenge (Anthropic) | $0.27 |
| **Total** | **$43.95** |

## ❌ FAIL — Require Re-adaptation (17)

- b28/c5786: ملا اسحاق ضیائی مضامین
- b34/c5673: أعجاز القرآن
- b34/c5703: عقل
- b34/c5690: سورۃ الفاتحۃ
- b27/c1037: کتاب وصایا ابلیس
- b24/c454: توحید فی النحج البلاغۃ
- b1/c1109: عاشر کی دعوت
- b18/c4626: ظاہری واقعات
- b19/c302: احکامات شریعت کی تاویل
- b29/c2521: لیالی الفاضلۃ
- b6/c330: مناقب
- b6/c661: نحج البلاغۃ کے خطبے
- b12/c3556: سیرت المناصیب
- b5/c346: عربی کے اشعار
- b16/c849: دعا و مناجات
- b16/c842: فجر کے بعد کی دعائیں
- b16/c851: روزانہ کی دس دعائیں

## ⚠ WARN — Review Before Proceeding (37)

These chapters passed validation but the LLM challenger raised concerns.
Review challenger reports before signing off.

- b34/c5718: آغاز اور مقاصد
- b34/c5708: دین اور سائنس
- b34/c5733: استعاذۃ
- b34/c5689: بسم اللہ الرحمن الرحیم
- b34/c5695: الحمد للہ رب العلمین
- b34/c5727: الرحمن الرحیم
- b34/c5720: مالک یوم الدین
- b34/c5762: ایاک نعبد و الصراط
- b34/c5756: Misconceptions Arguments
- b35/c6793: Miracles of Quran
- b35/c6807: The Human Spirit
- b36/c5767: Introduction
- b27/c1200: ولایت سے متعلق مضامین
- b27/c3589: اقوال الحکمۃ
- b24/c650: کلمۃ التوحید کی معرفت
- b24/c3: وجود مبدع کی حقانیت
- b24/c41: کلمہ التوحید کے مختلف ابواب
- b1/c1084: عقل اول
- b1/c1196: منبعثین
- b1/c1098: سات عقول
- b1/c1138: تشکیل عالم کون و فساد
- b1/c1153: نفوس اور ان کی اقسام
- b32/c4616: Controlling Lust For Food and Sex
- b18/c5741: حضرت نوح علیہ السلام
- b25/c1227: طہارت سے متعلق روایتیں
- b25/c816: نجاست سے طہارت
- b26/c1272: نماز سے متعلق احادیث
- b26/c1281: نماز کا بیان
- b26/c1284: مساجد کا بیان
- b26/c1287: نماز کے اوقات
- b26/c5723: ارکان نماز کے ممثولات
- b26/c1351: مبارک ایام کی نمازیں
- b29/c2509: الکواکب الدریۃ
- b6/c3598: نہج البلاغۃ فی العربیۃ
- b12/c799: حدود کبار
- b12/c3586: شخصیات
- b5/c328: مختلف مناقب

## Bilingual Reader

Start the Astro dev server:
```bash
cd podcast-reader && npm run dev
```
Then navigate to `http://localhost:4321/kashkole` to review any chapter.

## Next Step

After review:
```bash
# Intake KAHSKOLE into the podcast pipeline
# python scripts/podcast/intake_book.py --from-bundle <bundle_root>
```