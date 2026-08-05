# Arabic Integrity Report — spiritual-ethos

- Rule: R-ARABIC-INTEGRITY (fingerprint v1.0)
- Phase verified: `0b`
- Generated: 2026-08-05T20:26:26Z
- Verdict: FAIL

Forbidden = an Arabic span mutated/dropped/invented by an LLM pass with no
sanctioning provenance (canonical injection or glossary curation).

## AI-DROP — spans removed without sanction (1)

| NFC_text | Artifact | Anchor | Count |
|---|---|---|---|
| الروح العقل | _system/source/text/refined-english.md | {'line': 107} | 1 |

## AI-INVENT — spans introduced without sanction (123)

| NFC_text | Artifact | Anchor | Count |
|---|---|---|---|
| القدس | _system/source/text/refined-english.md | {'line': 364} | 2 |
| شریعۃ | _system/source/text/refined-english.md | {'line': 364} | 3 |
| زکوۃ | _system/source/text/refined-english.md | {'line': 364} | 1 |
| موحد | _system/source/text/refined-english.md | {'line': 364} | 1 |
| الحق | _system/source/text/refined-english.md | {'line': 366} | 7 |
| نفس | _system/source/text/refined-english.md | {'line': 368} | 3 |
| باطن | _system/source/text/refined-english.md | {'line': 370} | 1 |
| احسان | _system/source/text/refined-english.md | {'line': 370} | 4 |
| اسلام | _system/source/text/refined-english.md | {'line': 370} | 1 |
| ایمان | _system/source/text/refined-english.md | {'line': 370} | 1 |
| شیطان | _system/source/text/refined-english.md | {'line': 372} | 2 |
| ابلیس | _system/source/text/refined-english.md | {'line': 372} | 2 |
| سورۃ الفلق | _system/source/text/refined-english.md | {'line': 372} | 1 |
| قُلْ أَعُوذُ بِرَبِّ ٱلْفَلَقِ ۱ مِن شَرِّ مَا خَلَقَ ۲ | _system/source/text/refined-english.md | {'line': 372} | 1 |
| مِن شَرِّ مَا خَلَقَ | _system/source/text/refined-english.md | {'line': 372} | 1 |
| حق | _system/source/text/refined-english.md | {'line': 374} | 1 |
| وَضَعَ الشَّئُی حَقَّ مَحَلِّہِ | _system/source/text/refined-english.md | {'line': 376} | 2 |
| جبرئیل | _system/source/text/refined-english.md | {'line': 385} | 1 |
| يَا مُحَمَّدُ، أخْبِرْنِي عَنْ الإسْلاَمِ | _system/source/text/refined-english.md | {'line': 387} | 1 |
| الإِسْلاَمُ أَنْ تَشْهَدَ أَنْ لاَ إِلهَ إِلاَ اللهُ وَأَنَّ مُحَمَّداً رَسُولُ اللهِ، وَتُقِيمَ الصَّلاَةَ، وَتُؤْتِيَ الزَّكَاةَ، وَتَصُومَ رَمَضَانَ، وَتَحُجَّ الْبَيتَ إِن اسْتَطَعْتَ إِلَيْهِ سَبِيلاً | _system/source/text/refined-english.md | {'line': 387} | 1 |
| صَدَقْتَ | _system/source/text/refined-english.md | {'line': 387} | 2 |
| فَأَخْبِرْنِي عَنِ الإِيْمَانِ | _system/source/text/refined-english.md | {'line': 387} | 1 |
| أَنْ تُؤْمِنَ بِاللهِ، وَمَلاَئِكَتِهِ، وَكُتُبِهِ، وَرُسُلِهِ، وَالْيَوْمِ الآخِرِ، وَتُؤْمِنَ بِالْقَدَرِ خَيْرِهِ وَشَرِّهِ | _system/source/text/refined-english.md | {'line': 387} | 1 |
| فَأَخْبِرْنِي عَنِ الإِحْسَانِ | _system/source/text/refined-english.md | {'line': 387} | 1 |
| أَنْ تَعْبُدَ اللهَ كَأَنَّكَ تَرَاهُ، فَإِنْ لَمْ تَكُنْ تَرَاهُ فَإِنَّهُ يَرَاكَ | _system/source/text/refined-english.md | {'line': 387} | 1 |
| حَسَنَ | _system/source/text/refined-english.md | {'line': 389} | 1 |
| قبح | _system/source/text/refined-english.md | {'line': 389} | 1 |
| قبیح | _system/source/text/refined-english.md | {'line': 389} | 1 |
| نھج البلاغۃ | _system/source/text/refined-english.md | {'line': 395} | 1 |
| المُحسنین | _system/source/text/refined-english.md | {'line': 395} | 1 |
| سجدۃ | _system/source/text/refined-english.md | {'line': 395} | 1 |
| امام المتعصبین و سلف المستکبرین | _system/source/text/refined-english.md | {'line': 395} | 1 |
| الکریم | _system/source/text/refined-english.md | {'line': 444} | 2 |
| الرحمن الرحیم | _system/source/text/refined-english.md | {'line': 444} | 2 |
| خلیفۃ اللہ | _system/source/text/refined-english.md | {'line': 444} | 2 |
| عباد اللہ | _system/source/text/refined-english.md | {'line': 444} | 2 |
| يَٓأَيُّهَا ٱلنَّاسُ أَنتُمُ ٱلْفُقَرَآءُ إِلَى ٱللَّهِۖ وَٱللَّهُ هُوَ ٱلْغَنِىُّ ٱلْحَمِيدُ | _system/source/text/refined-english.md | {'line': 444} | 3 |
| وَلاَ تَنْصِبَنَّ نَفْسَكَ لِحَرْبِ اللهِ | _system/source/text/refined-english.md | {'line': 462} | 1 |
| الْكِبْرِيَاءُ رِدَائِي، وَالْعَظَمَةُ إِزَارِي، فَمَنْ نَازَعَنِي وَاحِدًا مِنْهُمَا، قَذَفْتُهُ فِي النَّارِ | _system/source/text/refined-english.md | {'line': 462} | 1 |
| لِّمَنِ ٱلْمُلْكُ ٱلْيَوْم لِلَّهِ ٱلْوَحِدِ ٱلْقَهَّارِ | _system/source/text/refined-english.md | {'line': 465} | 1 |
| القاسیۃ | _system/source/text/refined-english.md | {'line': 465} | 1 |
| إِذْ قَالَ رَبُّكَ لِلْمَلَٓئِكَةِ إِنِّى خَلِقٌۢ بَشَرًۭا مِّن طِينٍۢ ۝ فَإِذَا سَوَّيْتُهُۥ وَنَفَخْتُ فِيهِ مِن رُّوحِى فَقَعُوا۟ لَهُ سَجِدِينَ ۝ فَسَجَدَ ٱلْمَلَٓئِكَةُ كُلُّهُمْ أَجْمَعُونَ ۝ إِلَّآ إِبْلِيسَ ٱسْتَكْبَرَ وَكَانَ مِنَ ٱلْكَفِرِينَ | _system/source/text/refined-english.md | {'line': 465} | 1 |
| خلقتنی من نار و خلقتہ من طین | _system/source/text/refined-english.md | {'line': 465} | 1 |
| امام المُتَعَصِّبِین و سلف المستکبرین | _system/source/text/refined-english.md | {'line': 465} | 1 |
| الشِّرْكُ فِي هَذِهِ الْأُمَّةِ أَخْفَى مِنْ دَبِيبِ النَّمْلِ علی حَجَرِ الأَسوَد فِی لِیلَۃِ الظُّلْما | _system/source/text/refined-english.md | {'line': 470} | 1 |
| شرک الجلی | _system/source/text/refined-english.md | {'line': 470} | 1 |
| شرک الخفی | _system/source/text/refined-english.md | {'line': 470} | 1 |
| ریا | _system/source/text/refined-english.md | {'line': 470} | 1 |
| وَلاَ تَقُولَنَّ | _system/source/text/refined-english.md | {'line': 475} | 2 |
| إِنِّي مُؤَمَّرٌ | _system/source/text/refined-english.md | {'line': 475} | 1 |
| آمُرُ | _system/source/text/refined-english.md | {'line': 475} | 1 |
| فَأُطَاعُ | _system/source/text/refined-english.md | {'line': 475} | 1 |
| إِنَّ ذلِكَ إِدْغَالٌ فِي الْقَلْبِ، وَمَنْهَكَةٌ لِلدِّينِ | _system/source/text/refined-english.md | {'line': 475} | 1 |
| وضع کل شئی حق محلہ | _system/source/text/refined-english.md | {'line': 475} | 1 |
| وَإِذَا أَحْدَثَ لَكَ مَا أَنْتَ فِيهِ مِنْ سُلْطَانِكَ أُبَّهَةً أَوْ مَخِيلَةً، فَانْظُرْ إِلَى عِظَمِ مُلْكِ اللهِ فَوْقَكَ، فَإِنَّ ذلِكَ يُطَامِنُ إِلَيْكَ مِنْ طِمَاحِكَ، وَيَكُفُّ عَنْكَ مِنْ غَرْبِكَ،يَفِيءُ إِلَيْكَ بِمَا عَزَبَ عَنْكَ مِنْ عَقْلِكَ | _system/source/text/refined-english.md | {'line': 478} | 1 |
| مَخِيلَةً | _system/source/text/refined-english.md | {'line': 478} | 1 |
| خیال | _system/source/text/refined-english.md | {'line': 478} | 1 |
| مخیلۃ | _system/source/text/refined-english.md | {'line': 478} | 1 |
| كُلُّ شَىْءٍ هَالِكٌ إِلَّا وَجْهَهُ | _system/source/text/refined-english.md | {'line': 478} | 1 |
| كُلُّ مَنْ عَلَيْهَا فَانٍۢ ۝ وَيَبْقَىٰ وَجْهُ رَبِّكَ ذُو ٱلْجَلَلِ وَٱلْإِكْرَامِ | _system/source/text/refined-english.md | {'line': 478} | 1 |
| وَقُلْ جَآءَ ٱلْحَقُّ وَزَهَقَ ٱلْبَطِلُ ۚ إِنَّ ٱلْبَطِلَ كَانَ زَهُوقًۭا | _system/source/text/refined-english.md | {'line': 478} | 1 |
| إِيَّاكَ وَمُسَامَةَ اللهِ فِي عَظَمَتِهِ، وَالتَّشَبُّهَ بِهِ فِي جَبَرُوتِهِ، فَإِنَّ اللهَ يُذِلُّ كُلَّ جَبَّار، وَيُهِينُ كُلَّ مُخْتَال | _system/source/text/refined-english.md | {'line': 481} | 1 |
| أَنْصِفِ اللهَ وَأَنْصِفِ النَّاسَ مِنْ نَفْسِكَ، وَمِنْ خَاصَّةِ أَهْلِكَ، وَمَنْ لَكَ فِيهِ هَوىً مِنْ رَعِيَّتِكَ، فَإِنَّكَ إِلاَّ تَفْعَلْ تَظْلِمْ | _system/source/text/refined-english.md | {'line': 481} | 1 |
| وَمَنْ ظَلَمَ عِبَادَ اللهِ كَانَ اللهُ خَصْمَهُ دُونَ عِبَادِهِ، وَمَنْ خَاصَمَهُ اللهُ أَدْحَضَ حُجَّتَهُ، وَكَانَ لله حَرْباً حَتَّى يَنْزعَ وَيَتُوبَ | _system/source/text/refined-english.md | {'line': 481} | 1 |
| فطرۃ | _system/source/text/refined-english.md | {'line': 483} | 1 |
| استدراج | _system/source/text/refined-english.md | {'line': 486} | 1 |
| درج | _system/source/text/refined-english.md | {'line': 486} | 1 |
| درجہ بدرجہ | _system/source/text/refined-english.md | {'line': 486} | 1 |
| وَمِمَّنْ خَلَقْنَآ أُمَّةٌۭ يَهْدُونَ بِٱلْحَقِّ وَبِهِ يَعْدِلُونَ ۝ وَٱلَّذِينَ كَذَّبُوا۟ بِـَٔايَتِنَا سَنَسْتَدْرِجُهُم مِّنْ حَيْثُ لَا يَعْلَمُونَ | _system/source/text/refined-english.md | {'line': 486} | 1 |
| وَلَا تُعْجِبْكَ أَمْوَلُهُمْ وَأَوْلَدُهُمْ ۚ إِنَّمَا يُرِيدُ ٱللَّهُ أَن يُعَذِّبَهُم بِهَا فِى ٱلدُّنْيَا وَتَزْهَقَ أَنفُسُهُمْ وَهُمْ كَفِرُونَ | _system/source/text/refined-english.md | {'line': 486} | 1 |
| ضمیر | _system/source/text/refined-english.md | {'line': 491} | 1 |
| وَنَفْسٍۢ وَمَا سَوَّىٰهَا | _system/source/text/refined-english.md | {'line': 491} | 1 |
| فَأَلْهَمَهَا فُجُورَهَا وَتَقْوَىٰهَا | _system/source/text/refined-english.md | {'line': 491} | 1 |
| وَإِذْ أَخَذَ رَبُّكَ مِنۢ بَنِىٓ آدَمَ مِن ظُهُورِهِمْ ذُرِّيَّتَهُمْ وَأَشْهَدَهُمْ عَلَىٰٓ أَنفُسِهِمْ أَلَسْتُ بِرَبِّكُمْ ۖ قَالُوا۟ بَلَىٰ ۛ شَهِدْنَآ ۛ أَن تَقُولُوا۟ يَوْمَ ٱلْقِيَمَةِ إِنَّا كُنَّا عَنْ هَذَا غَفِلِينَ | _system/source/text/refined-english.md | {'line': 493} | 1 |
| ۱۷۲ | _system/source/text/refined-english.md | {'line': 493} | 1 |
| النفس الامارۃ بالسوء | _system/source/text/refined-english.md | {'line': 495} | 1 |
| إِنِّي مُؤَمَّرٌ آمُرُ فَأُطَاعُ | _system/source/text/refined-english.md | {'line': 495} | 1 |
| مجاھدۃ النفس | _system/source/text/refined-english.md | {'line': 497} | 1 |
| محمد بن ابی بکر | _system/source/text/refined-english.md | {'line': 497} | 1 |
| مالک اشتر | _system/source/text/refined-english.md | {'line': 497} | 1 |
| كَلَّآ إِنَّ ٱلْإِنسَنَ لَيَطْغَىٰٓ | _system/source/text/refined-english.md | {'line': 497} | 1 |
| أَن رَّآهُ ٱسْتَغْنَىٰٓ | _system/source/text/refined-english.md | {'line': 497} | 1 |
| أَفَرَءَيْتَ مَنِ ٱتَّخَذَ إِلَهَهُۥ هَوَىٰهُ | _system/source/text/refined-english.md | {'line': 497} | 1 |
| وَلاَ تُدْخِلَنَّ فِي مَشُورَتِكَ بَخِيلاً يَعْدِلُ بِكَ عَنِ الْفَضْلِ، وَيَعِدُكَ الْفَقْرَ، وَلاَ جَبَاناً يُضعِّفُكَ عَنِ الاْمُورِ، وَلاَ حَرِيصاً يُزَيِّنُ لَكَ الشَّرَهَ بِالْجَوْرِ، فَإِنَّ الْبُخْلَ وَالْجُبْنَ وَالْحِرْصَ غَرَائِزُ شَتَّى يَجْمَعُهَا سُوءُ الظَّنِّ بِاللهِ | _system/source/text/refined-english.md | {'line': 534} | 1 |
| سُوءُ الظَّنِّ بِاللهِ | _system/source/text/refined-english.md | {'line': 538} | 1 |
| حسن الظن | _system/source/text/refined-english.md | {'line': 538} | 1 |
| وَكُلٌّ قَدْ سَمَّى اللهُ سَهْمَهُ، وَوَضَعَ عَلَى حَدِّهِ وَفَرِيضَتِهِ فِي كِتَابِهِ أَوْ سُنَّةِ نَبِيِّهِ | _system/source/text/refined-english.md | {'line': 552} | 1 |
| صلى الله عليه وآله | _system/source/text/refined-english.md | {'line': 552} | 1 |
| عَهْداً مِنْهُ عِنْدَنَا مَحْفُوظاً | _system/source/text/refined-english.md | {'line': 552} | 1 |
| عہد | _system/source/text/refined-english.md | {'line': 556} | 1 |
| أَفَمَن يَعْلَمُ أَنَّمَآ أُنزِلَ إِلَيْكَ مِن رَّبِّكَ ٱلْحَقُّ كَمَنْ هُوَ أَعْمَىٰٓ ۚ إِنَّمَا يَتَذَكَّرُ أُو۟لُوا۟ ٱلْأَلْبَبِ | _system/source/text/refined-english.md | {'line': 558} | 1 |
| ۱۹ | _system/source/text/refined-english.md | {'line': 558} | 1 |
| ٱلَّذِينَ يُوفُونَ بِعَهْدِ ٱللَّهِ وَلَا يَنقُضُونَ ٱلْمِيثَقَ | _system/source/text/refined-english.md | {'line': 558} | 1 |
| ۲۰ | _system/source/text/refined-english.md | {'line': 558} | 1 |
| وَلَا تَقْرَبُوا۟ مَالَ ٱلْيَتِيمِ إِلَّا بِٱلَّتِى هِىَ أَحْسَنُ حَتَّىٰ يَبْلُغَ أَشُدَّهُۥ ۚ وَأَوْفُوا۟ بِٱلْعَهْدِ ۖ إِنَّ ٱلْعَهْدَ كَانَ مَسْـُٔولًۭا | _system/source/text/refined-english.md | {'line': 562} | 1 |
| ۳۴ | _system/source/text/refined-english.md | {'line': 562} | 1 |
| وَأَكْثِرْ مُدَارَسَةَ الَعُلَمَاءِ، وَمُنَافَثَةَ الْحُكَمَاءِ، فِي تَثْبِيتِ مَا صَلَحَ عَلَيْهِ أَمْرُ بِلاَدِكَ، وَإِقَامَةِ مَا اسْتَقَامَ بِهِ النَّاسُ قَبْلَكَ | _system/source/text/refined-english.md | {'line': 568} | 1 |
| علماء | _system/source/text/refined-english.md | {'line': 570} | 1 |
| حکما | _system/source/text/refined-english.md | {'line': 570} | 1 |
| لو کشف الغطاء ما ازدت یقینا | _system/source/text/refined-english.md | {'line': 808} | 1 |
| فنیٰ | _system/source/text/refined-english.md | {'line': 998} | 1 |
| نھج البلاغہ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| خطبۃ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| الحَمْدُ للهِ الَّذَي لاَ يَبْلُغُ مِدْحَتَهُ القَائِلُونَ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| وَلاِ يُحْصِي نَعْمَاءَهُ العَادُّونَ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| ولاَ يُؤَدِّي حَقَّهُ الُمجْتَهِدُونَ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| الَّذِي لاَ يُدْركُهُ بُعْدُ الهِمَمِ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| وَلاَ يَنَالُهُ غَوْصُ الفِطَنِ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| الَّذِي لَيْسَ لِصِفَتِهِ حَدٌّ مَحْدُودٌ، وَلاَ نَعْتٌ مَوْجُودٌ، وَلا وَقْتٌ مَعْدُودٌ | _system/source/text/refined-english.md | {'line': 1047} | 1 |
| أخلاص | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| نفی الصفۃ | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| رحمن | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| رحیم | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| عزیز | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| لا الہ | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| نفی | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| الا اللہ | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| اثبات | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| سُبْحَنَ ٱللَّهِ عَمَّا يَصِفُونَ | _system/source/text/refined-english.md | {'line': 1049} | 1 |
| جزیۃ | _system/source/text/refined-english.md | {'line': 1121} | 1 |
| خَرَج | _system/source/text/refined-english.md | {'line': 1121} | 1 |
| سنۃ | _system/source/text/refined-english.md | {'line': 1121} | 1 |
| كَبُرَ مَقْتًا عِندَ ٱللَّهِ أَن تَقُولُوا۟ مَا لَا تَفْعَلُونَ | _system/source/text/refined-english.md | {'line': 1181} | 1 |

## AI-VOWEL-DRIFT — tashkeel altered on a protected span (0)

_None._

