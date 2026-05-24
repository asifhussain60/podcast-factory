# Name Mangling Map — Kitab al-Riyad (book-specific)

Loaded by `scripts/podcast/audit_transcript.py` via `load_book_mangle_map(BOOK_DIR)`
and merged into the global `NAME_MANGLING_MAP` (per-book wins on conflict).

The global map holds generic Arabic / Islamic vocabulary likely to appear across
any Islamic-source book. This file holds names specific to *Kitab al-Riyad*:
the book's own title, the lost source it disputes, the two disputant works,
and the historical figures and works named in this book that are unlikely to
appear in other books in the corpus.

Format: markdown pipe table. One row per canonical name. Mangled forms are
comma-separated within the second cell. Match is case-insensitive substring.

| Canonical | Mangled forms (comma-separated) |
|---|---|
| Kitab al-Riyad | kitab al riyad, kitabar riyad, kitab arriyad, kitab al riad, kitabar-riad, keytab al riyad, keytab arriad |
| al-Kirmani | al kermany, al kirmani, alkirmany, alkermany, el kirmani, al cher mani, al krimani, al kearmani |
| Hamid al-Din | hameedaldeen, hameed aldeen, hamid aldeen, hamid eldeen, hamidal deen |
| Kitab al-Mahsul | kitabal mahsul, kitab almahsool, kitab al ma sool, kitab al mahsul, kitab almahsool |
| al-Mahsul | almahsool, al mahsool, al mahsul, almasool, almasul, al ma sool |
| al-Islah | al islah, alislah, al islaah, alislaah, al islac, al islaa |
| al-Nusra | al nusra, alnusra, an nusra, annusra, al nasra |
| Abu Hatim al-Razi | abu hateem al razi, abuhatim al raazi, abu hatim al razi |
| Abu Bakr al-Razi | abu baker al razi, abu bakr al razi, abubakr al raazi |
| al-Sijistani | al sijistani, al sij is tani, al sigistani, al seejistani |
| al-Nasafi | al nasafi, al nasafey, al nassafi, al nessefi |
| Rahat al-'Aql | rahat al akl, rahat al aqal, rahat al akal, rahat alaql |
| al-Masabih fi al-Imama | almasabih fil imama, al masabeeh fil imamah, almasabeh fil imama |
| al-Rawda | al rawda, alrawda, al rauda, ar rauda, al raudah |
| Mabasim al-Bisharat | mabasim al bisharat, mabaseem al bisharaat, mabasim al bishaarat |
| al-Aqwal al-Dhahabiyya | al aqwal al dhahabiyyah, al aqwal al zahabiyya, al akwal al dhahabiya |
| Hujjat al-Iraqayn | hujjat al iraqayn, hujjat al iraqain, hujat aliraqayn |
| al-Hakim bi-Amr Allah | al hakim bi amrillah, al hakim biamr allah, al haakim bi amr allah |
| al-Muʿizz li-Dīn Allāh | al muizz lideenillah, al mueez lideen allah, al moez li deen allah |
| al-ʿAziz bi-llah | al aziz billah, al azeez billah, al aazeez billah |
| Bandhaqlis | bandakleez, band ha qlees, ban thaq lis, bandhaqlees |
| Empedocles | empedoklees, empidoclees, empedokleez |
| al-qa'im / al-Qā'im | alqaaim, al qaim, alqaim, al qa im, al qayim |
| natiq / al-natiq | naa tik, anaatik, al na tik, an natik, al naa tiq |
| nutaqā' | new ta qaa, nutaqaa, nu ta qua, nu taqa |
| ḥujjas / hujaj | hujjas, hujaj, hujjajs, hujajs, hudjadj |
| mansak | mansek, mansaak, man sak |
| qurban / al-qurban | qur baan, qurbaan, kurban, qurban |
| ʿitra al-ṭāhira | itrah at taahirah, itra al tahira, itra at tahira |
| ibdāʿ | ibdaa, ib daa, ibda, ibdaag |
| al-shayʾ | ash shay, al shey, al shay, al shai |
| la-shayʾ | laa shay, la shey, la shai, lashay |
| al-Bāriʾ | al baari, al baar i, al bari, albari |
| al-Khāliq | al khaalik, al khaalig, al khalik, al khaalec |
| al-Kalima | al kalimah, alkalimah, al kelima, alkelimah |
| al-ʿaql al-awwal | al akl al awal, al aql al awal, alaqlal awwal |
| al-asās | al asaas, al asas, alasaas, al as ass |
| bāb / abwāb | baab, abwab, ab waab, ab wab |
| fasl / fusūl | fasl, fusool, fusul, fu sool |
| Muhammad ibn Abi Bakr | muhammad ibn abi bakar, muhammad ibn abi baker, muhammad ibn abuubakr |
| Zayn al-'Abidin | zaynalabideen, zayn al aabideen, zayn al abedeen |
| al-Sahifa al-Sajjadiyya | as sahifa as sajjadiyya, as sahifah as sajjadiyya, sahifa sajjadiya |
| bayt al-maqdis | baytal maqdis, bait al maqdis, beytal maqdis |
