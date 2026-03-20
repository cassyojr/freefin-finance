"""
Exact Python port of index.html parsing logic.
Compares:
  (A) Official total read from PDF
  (B) Sum of all parsed+deduped transactions
Prints full diagnostics so mismatches can be fixed.
"""
import re, unicodedata
from pypdf import PdfReader

PDF = r'c:\Users\cassy\OneDrive\Área de Trabalho\Extrato\01-2024.pdf'

# quick duplicate check across entire PDF
_reader2 = PdfReader(PDF)
_all_tx = []
_MONEY = re.compile(r'(\d{2}/\d{2})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})')
for _page in _reader2.pages:
    for _l in _page.extract_text(extraction_mode='layout').split('\n'):
        for _m in _MONEY.finditer(_l.strip()):
            _all_tx.append((_m.group(1), _m.group(3)))
from collections import Counter as _Counter
_counts = _Counter(_all_tx)
print("=== Transactions appearing MORE THAN ONCE across entire PDF ===")
for k, v in sorted(_counts.items(), key=lambda x: -x[1]):
    if v > 1:
        print(f"  {v}x  {k[0]}  {k[1]}")
print(f"Total raw tx in PDF: {len(_all_tx)},  unique: {len(_counts)}")

# ── 1. extractText  (mirrors pdf.js Y-grouping) ───────────────────────────────
reader = PdfReader(PDF)
raw_lines = []
for page in reader.pages:
    last_y   = None
    cur_line = ''
    # use layout mode so multi-column pages come through in reading order
    for item in page.extract_text(extraction_mode='layout').split('\n'):
        raw_lines.append(item.rstrip())

lines = [l.strip() for l in raw_lines if l.strip()]

print(f"Total raw lines from PDF: {len(lines)}")

# ── 2. extractTotalFromTextLines ──────────────────────────────────────────────
TOTAL_LABELS = ['lançamentos atuais', 'valor da fatura atual', 'total da sua fatura']
official_total = 0.0
for i, l in enumerate(lines):
    if any(lbl in l.lower() for lbl in TOTAL_LABELS):
        nums = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', l)
        if nums:
            val = float(nums[-1].replace('.', '').replace(',', '.'))
            if val > 100:
                official_total = val
                print(f'Found total label on line {i}: {repr(l[:80])}')
                print(f'  -> parsed total: {official_total:.2f}')
                break
        if i + 1 < len(lines):
            nums = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', lines[i + 1])
            if nums:
                val = float(nums[-1].replace('.', '').replace(',', '.'))
                if val > 100:
                    official_total = val
                    print(f'Found total label on line {i}, value on line {i+1}: {repr(lines[i+1][:80])}')
                    print(f'  -> parsed total: {official_total:.2f}')
                    break

# ── 3. extractRelevantLines ───────────────────────────────────────────────────
in_section   = False
in_future    = False
relevant     = []
section_log  = []    # for debugging section boundaries

for idx, line in enumerate(lines):
    has_lanc = 'Lançamentos: compras e saques' in line
    has_parc = 'compras parceladas' in line.lower()

    starts_with_date = bool(re.match(r'^\d{2}/\d{2}', line))

    if has_lanc:
        in_section = True
        section_log.append(f'  L{idx}: SECTION START -> {repr(line[:80])}')

    # Only stop on non-transaction lines (right-column-only lines)
    if not starts_with_date and 'Encargos cobrados nesta fatura' in line:
        section_log.append(f'  L{idx}: SECTION STOP  -> {repr(line[:80])}')
        in_section = False
        in_future  = False

    if has_parc:
        in_future = True
        section_log.append(f'  L{idx}: FUTURE MODE ON -> {repr(line[:80])}')
        continue

    if has_lanc:
        continue
    if in_future:
        continue

    if in_section:
        if not starts_with_date:
            continue  # category/city label, skip
        # Multi-amount line: keep left column only (truncate to first amount)
        amounts = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', line)
        if len(amounts) > 1:
            m = re.match(r'^(.+?\d{1,3}(?:\.\d{3})*,\d{2})', line)
            relevant.append(m.group(1).strip() if m else line)
        else:
            relevant.append(line)

print(f"\nSection boundary events:")
for s in section_log:
    print(s)

print(f"\nRelevant lines kept: {len(relevant)}")
print("\n--- All relevant lines (first 80) ---")
for i, r in enumerate(relevant[:80]):
    amounts = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', r)
    print(f"  [{i:3d}] {len(amounts)}amt | {repr(r[:100])}")

print("\n--- Raw PDF lines 180-200 ---")
for i in range(180, min(200, len(lines))):
    nums = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', lines[i])
    print(f"  [{i:3d}] ({len(nums)}n) {repr(lines[i][:160])}")

# Print raw lines around section starts for debugging
print("\n--- Raw lines around section events ---")
evt_lines = [int(s.split(':')[0].strip().lstrip('L')) for s in section_log]
for el in sorted(set(evt_lines)):
    for i in range(max(0, el-1), min(len(lines), el+4)):
        amounts = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', lines[i])
        print(f"  [{i:3d}] ({len(amounts)} amounts) {repr(lines[i][:120])}")
    print()

# ── 4. parseExpenses ──────────────────────────────────────────────────────────
SKIP_WORDS = ['total', 'fatura', 'pagamento', 'saldo', 'anterior',
              'iof', 'encargo', 'anuidade', 'seguro', 'tarifa', 'juros']
MONEY_RE   = re.compile(r'(\d{2}/\d{2})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})')
INST_RE    = re.compile(r'(\d{2})/(\d{2})')

def clean(t):
    return re.sub(r'\s+', ' ', t.replace('*', '').replace('-CT', '')).strip()

expenses = []
skipped  = []
for line in relevant:
    for m in MONEY_RE.finditer(line):
        date  = m.group(1)
        desc  = clean(m.group(2))
        inst_m = INST_RE.search(desc)
        inst   = None
        if inst_m:
            inst = (int(inst_m.group(1)), int(inst_m.group(2)))
        raw   = m.group(3)
        lower = desc.lower()
        if any(k in lower for k in SKIP_WORDS):
            skipped.append({'date': date, 'desc': desc, 'value': raw, 'reason': 'filter'})
            continue
        value = float(raw.replace('.', '').replace(',', '.'))
        expenses.append({'date': date, 'desc': desc, 'value': value, 'inst': inst})

# ── 5. deduplicateExpenses ────────────────────────────────────────────────────
def normalize(t):
    t = t.lower()
    t = unicodedata.normalize('NFD', t)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

unique      = []
strict_seen = set()
norm_seen   = set()
dupes       = []

for e in expenses:
    vk = f"{e['value']:.2f}"
    ik = f"{e['inst'][0]}/{e['inst'][1]}" if e['inst'] else '-'
    sk = f"{e['date']}|{e['desc']}|{vk}|{ik}"
    nk = f"{e['date']}|{normalize(e['desc'])}|{vk}|{ik}"
    if sk in strict_seen or nk in norm_seen:
        dupes.append(e)
        continue
    strict_seen.add(sk)
    norm_seen.add(nk)
    unique.append(e)

# ── 6. Results ────────────────────────────────────────────────────────────────
calc = round(sum(e['value'] for e in unique), 2)
diff = round(calc - official_total, 2)

print(f"\n{'='*60}")
print(f"Official total (PDF):  {official_total:.2f}")
print(f"Calculated sum:        {calc:.2f}")
print(f"Difference:            {diff:+.2f}")
print(f"Transactions kept:     {len(unique)}")
print(f"Duplicates removed:    {len(dupes)}")
print(f"Filtered (junk):       {len(skipped)}")
print(f"{'='*60}")

if dupes:
    print("\n--- Removed as duplicates ---")
    for d in dupes:
        ik = f"[{d['inst'][0]}/{d['inst'][1]}]" if d['inst'] else ''
        print(f"  {d['date']}  {d['value']:>9.2f}  {d['desc']} {ik}")

if skipped:
    print("\n--- Filtered out (junk) ---")
    for s in skipped:
        print(f"  {s['date']}  {s['value']:>12}  {s['desc']}")

if abs(diff) > 0.05:
    direction = "HIGHER" if diff > 0 else "LOWER"
    print(f"\n>>> MISMATCH: sum is {direction} by {abs(diff):.2f}")
    print(f"\n{'Date':<8}  {'Value':>9}  Description")
    print('-' * 72)
    for e in unique:
        ik = f"  [{e['inst'][0]}/{e['inst'][1]}]" if e['inst'] else ''
        print(f"{e['date']:<8}  {e['value']:>9.2f}  {e['desc']}{ik}")
else:
    print("\n✅ Totals match!")
