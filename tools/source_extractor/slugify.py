"""Slugification for KAHSKOLE (Urdu/Arabic script) and KSESSIONS (English) names.

KAHSKOLE: best-effort Urdu/Arabic → ASCII transliteration. Falls back to a
short manual map for common stems; otherwise produces a placeholder slug
that includes the DB ID so the filesystem is always unambiguous.
"""
from __future__ import annotations
import re, unicodedata

URDU_STEM_MAP = {
    "کتاب": "kitab", "رسالہ": "risala", "رسالۃ": "risala",
    "مفاتیح": "mafatih", "الحکمۃ": "al-hikmah", "الحکمت": "al-hikmah",
    "علوم": "uloom", "مبدا": "mabda", "معاد": "maad",
    "تشکیل": "tashkeel", "عالم": "aalam", "روحانی": "ruhani", "حیات": "hayat",
    "کون": "kawn", "فساد": "fasad",
    "عقل": "aql", "اول": "awwal", "سات": "saat", "عقول": "uqool",
    "منبعثین": "munbathin", "عاشر": "aashir", "دعوت": "dawat",
    "موالید": "mawalid", "پیدائش": "paydaish",
    "نفوس": "nufoos", "اقسام": "aqsam",
    "مزموم": "mazmoom", "محمود": "mahmood",
    "مراتب": "maratib", "مجامع": "majame",
    "مصباح": "misbah", "الشریعۃ": "al-shariah", "الشریعت": "al-shariah",
    "حکمت": "hikmat", "الموت": "al-mawt",
    "العالم": "al-aalim", "والغلام": "wal-ghulam",
    "حکایات": "hikayat", "بنی": "bani", "اسرائیل": "israil",
    "منتخب": "muntakhab", "علمی": "ilmi", "مضامین": "mazameen",
    "اشعار": "ashaar", "غزالی": "ghazali", "کیمیائی": "kimiya",
    "السعادۃ": "as-saadah",
    "دعائم": "daaim", "الاسلام": "al-islam", "ولایت": "wilayat",
    "طہارت": "taharat", "صلواۃ": "salawat", "الصوم": "as-sawm",
    "الحج": "al-hajj", "زکواۃ": "zakat",
    "آداب": "adab", "اخلاق": "akhlaq", "حسنۃ": "hasana",
    "قرآنی": "qurani", "قصص": "qisas", "الانبیا": "al-anbiya",
    "علی": "ali", "ابن": "ibn", "ابی": "abi", "طالب": "talib",
    "علیہ": "alayhi", "السلام": "as-salam",
    "کلمات": "kalimat", "ربانی": "rabbani", "تاویلات": "taweelat",
    "توحید": "tawheed", "مبدع": "mubdi", "تعالی": "taala",
    "ضروری": "zaroori", "معلومات": "maloomat",
    "ظاہر": "zahir", "باطن": "batin", "ازدواج": "izdiwaj",
    "علم": "ilm", "اور": "aur",
    "قضا": "qaza", "قصاص": "qisas",
    "مستفید": "mustafid", "کے": "ke", "خواص": "khawas",
    "الماہیتہ": "al-mahiya", "والذرۃ": "wadh-dharra", "والالم": "wal-alam",
    "منصیب": "manasib", "دعات": "daat", "سیرت": "seerah", "واقعات": "waqiat",
    "مجموعۃ": "majmua", "دعاؤں": "duaaon", "کا": "ka",
    "مسودے": "musawwadat",
    "آیات": "ayaat", "سورۃ": "surah", "تاویل": "taweel",
    "و": "wa", "في": "fi", "علی": "ali", "من": "min", "الی": "ila",
    "بسم": "bism", "اللہ": "allah", "الرحمن": "ar-rahman", "الرحیم": "ar-rahim",
    "خطبہ": "khutba", "کمیل": "kumayl",
}


def slugify_english(text: str, max_len: int = 40) -> str:
    """English text → kebab-case slug, NFKD-normalized, ASCII-safe."""
    t = unicodedata.normalize("NFKD", text)
    t = t.encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    t = re.sub(r"-{2,}", "-", t)
    if len(t) > max_len:
        t = t[:max_len].rstrip("-")
    return t or "untitled"


def slugify_urdu(text: str, db_id: int, max_len: int = 40) -> str:
    """Urdu/Arabic → ASCII slug using URDU_STEM_MAP. Unknown words become a
    short fingerprint. The DB ID is NOT appended (caller can add it if needed)
    but always available as a tie-breaker."""
    words = re.findall(r"[؀-ۿݐ-ݿ]+", text)
    if not words:
        return slugify_english(text) or f"id-{db_id}"

    out_parts = []
    for w in words:
        mapped = URDU_STEM_MAP.get(w)
        if mapped:
            out_parts.append(mapped)
        else:
            fp = "x" + format(sum(ord(c) for c in w) % 9999, "04d")
            out_parts.append(fp)

    slug = "-".join(out_parts)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug or f"id-{db_id}"


if __name__ == "__main__":
    samples = [
        ("منتخب علمی مضامین", 23),
        ("علوم مبدا و معاد", 1),
        ("عقل اول", 74),
        ("کتاب مصباح الشریعۃ", 38),
        ("رسالہ حکمت الموت", 999),
        ("توحید مبدع تعالی", 24),
    ]
    print("URDU:")
    for name, id_ in samples:
        print(f"  {id_:>4}  {name}  →  {slugify_urdu(name, id_)}")
    print("\nENGLISH:")
    for name in ["The Origin", "MABDA MA'AD", "Physical Universe", "TAWHEED (Unity)",
                 "The First Intellect", "Asaas Al-Taveel"]:
        print(f"  {name!r}  →  {slugify_english(name)}")
