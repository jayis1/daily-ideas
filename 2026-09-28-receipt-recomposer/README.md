# Receipt Recomposer

Receipt Recomposer is a dependency-free Python CLI that finds which groups of receipt items exactly equal a mystery subtotal. It uses integer cents rather than floating-point arithmetic, so a match is exact and repeatable.

## Why

A card statement, reimbursement, or shared bill may show only a partial total. Given the itemized receipt, Receipt Recomposer can identify the possible groups behind that amount without uploading financial data.

## Requirements

- Python 3.8 or newer
- No third-party packages, accounts, or network access

## Run

From the repository root:

```bash
cd 2026-09-28-receipt-recomposer
python3 receipt_recomposer.py --target 5.00 'Tea=2.50' 'Cake=3.75' 'Pen=1.25'
```

Verified output:

```text
Exact combinations for $5.00:
1. Cake ($3.75) + Pen ($1.25)
```

Prices may have a leading `$` and one or two decimal places. Quote arguments containing spaces or a dollar sign so the shell passes them unchanged.

For a longer receipt, create a UTF-8 file with one `NAME=PRICE` item per line. Blank lines and lines beginning with `#` are ignored:

```text
# team lunch
Soup=4.50
Bread=2.00
Tea=2.50
Cake=3.75
Pen=1.25
```

Then run:

```bash
python3 receipt_recomposer.py --target 8.25 --file receipt.txt
```

Command-line items and file items can be combined. Restrict the group size, cap results, or request JSON:

```bash
python3 receipt_recomposer.py --target 5.00 --min-items 2 --max-items 3 --limit 5 --json \
  'Tea=2.50' 'Cake=3.75' 'Pen=1.25'
```

Show all options:

```bash
python3 receipt_recomposer.py --help
```

## Behavior and limits

- Searches combinations from the smallest allowed size upward while preserving input order.
- Treats equal-priced entries as separate receipt items.
- Accepts no more than 24 items to keep exhaustive combination search bounded.
- Rejects negative amounts, zero-priced items, malformed prices, and prices with fractional cents.
- A successful search with no match exits with status 0 and says that no exact combination exists.

## Tests

Run the focused test suite from this directory:

```bash
python3 -m unittest -v
```

The tests cover exact money parsing, invalid values, item parsing, deterministic match order, duplicate prices, size and result limits, receipt files, text output, JSON output, and no-match behavior.
