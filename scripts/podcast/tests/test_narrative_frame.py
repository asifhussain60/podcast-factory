def test_vowelling_check_sees_past_a_lightly_marked_scan_span() -> None:
    # The blind spot that reached print: the scan carried three marks in
    # twenty-three words, and the old rule built its haystack only from scan
    # spans with NO marks at all — so those three marks disqualified the whole
    # span from being a witness and exempted everything inside it.
    from _narrative import ocr_vowelling_findings

    scan = "قال الشيخ وصلى الله على من اختاره من عباده وجعله للعالمين نذيراً"
    book = "> وَصَلَّى اللَّهُ عَلَى مَنِ اخْتَارَهُ مِنْ عِبَادِهِ وَجَعَلَهُ لِلْعَالَمِينَ نَذِيرًا\n"

    findings = ocr_vowelling_findings(book, scan)

    assert findings and "vowelled beyond the scan" in findings[0]


def test_a_run_matching_its_scans_own_vowelling_is_not_flagged() -> None:
    from _narrative import ocr_vowelling_findings

    scan = "وَصَلَّى اللَّهُ عَلَى مَنِ اخْتَارَهُ مِنْ عِبَادِهِ"
    book = "> وَصَلَّى اللَّهُ عَلَى مَنِ اخْتَارَهُ مِنْ عِبَادِهِ\n"

    assert ocr_vowelling_findings(book, scan) == []


def test_a_word_the_scan_never_carries_is_not_accused() -> None:
    # No evidence either way is not evidence of fabrication.
    from _narrative import ocr_vowelling_findings

    assert ocr_vowelling_findings("> كَلِمَاتٌ لَيْسَتْ فِي الْمَسْحِ أَبَدًا\n", "نص مختلف تماما هنا") == []
