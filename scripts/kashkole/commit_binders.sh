#!/usr/bin/env bash
# Commit one binder at a time (per per-binder unit-of-resume rule).
set -e
cd "$(git rev-parse --show-toplevel)"

# binder_id : shelf_prefix : name
declare -a BINDERS=(
  "36:04-islam-iman-ihsan:ISLAM IMAN IHSAN"
  "27:05-adab-wa-akhlaq-hasana:آداب و اخلاق حسنہ"
  "24:06-tawheed-mubdi-taala:توحید مبدع تعالی"
  "23:08-muntakhab-ilmi-mazameen:منتخب علمی مضامین"
  "32:09-ghazali-kimiya-as-saadah:غزالی - کیمیائی السعادۃ"
  "8:10-kalimat-rabbani-ki-taweelat:کلمات ربانی کی تاویلات"
  "18:11-qurani-qisas-al-anbiya-ke-x7934:قرآنی قصص الانبیا کے حقائق"
  "19:12-daaim-al-islam-wilayat:دعائم الاسلام : ولایت"
  "25:13-daaim-al-islam-taharat:دعائم الاسلام : طہارت"
  "26:14-daaim-al-islam-salawat:دعائم الاسلام : صلواۃ"
  "29:16-daaim-al-islam-as-sawm:دعائم الاسلام : الصوم"
  "6:18-ali-ibn-abi-talib-alayhi-as-salam:علی ابن ابی طالب علیہ السلام"
  "12:19-daat-aur-x9691-ki-seerah-wa-waqiat:دعات اور مناصیب کی سیرت و واقعات"
  "5:20-muntakhab-ashaar:منتخب اشعار"
  "16:21-muntakhab-duaaon-ka-majmua:منتخب دعاؤں کا مجموعہ"
)

for entry in "${BINDERS[@]}"; do
  IFS=':' read -r BID PREFIX NAME <<< "$entry"
  DIR="_workspace/kashkole-ksessions/extracted/kashkole/${PREFIX}"
  if [[ ! -d "$DIR" ]]; then
    echo "SKIP: $DIR not found for binder $BID"
    continue
  fi
  git add "$DIR"
  if git diff --cached --quiet; then
    echo "SKIP: no changes for binder $BID ($NAME)"
    continue
  fi
  echo "Committing binder $BID — $NAME"
  git commit -m "feat(kashkole): binder ${BID} — ${NAME} (autonomous run)" \
    -m "Bundles prepared, vision pass deferred to human reviewer (stub sidecars — flagged needs_human_review for image content), finalized, reviewed against curated Ismaili glossary, and sealed. See _workspace/plan/kashkole-rollout-failures.log for the chapters whose images are flagged for human vision review." \
    -m "Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
done
