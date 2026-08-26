#!/usr/bin/env python3
"""Build the Grim Dawn records SQLite database from the raw .dbr dumps.

Converts every .dbr file under test/records/items and test/records/skills (the only two
subfolders the website needs) into one normalized SQLite database:

    records(path, stat, value, is_list)   PK (path, stat)
    meta(key, value)

  * one row per stat per record; `path` is stored without the .dbr extension, with
    forward slashes, relative to the records/ root — the same form the SDK loaders use
    (e.g. 'items/gearaccessories/waist/b202f_waist').
  * scalar lines (`key,value,`) store the raw value text in `value`.
  * multi-value lines (`key,v1,v2,...`) store the FULL list as a JSON array in `value`
    with `is_list = 1`, elements typed: int when the text is an integer, float when it is
    a decimal, string otherwise. The game uses these for tiered fields, e.g.
    `augmentSkillLevel1,0,0,3,` or `racialBonusRace,Race002,Race012,`.
  * lines whose value is empty or numeric zero are dropped at build time (judged by a
    list's last element) — the same "both value and textvalue empty" filter the exe's
    input dump applied. Everything else is stored, so the DB holds every stat a record
    actually carries, with no zero-noise rows.

The database is the production record store for the website. This script only builds
it; everything read back out of the DB after the build — load_record(),
set_bonuses(), apply_equipment_skill_bonuses() — lives in records_api.py.

Usage:
    python test/build_records_db.py                  # build test/records.db
    python test/build_records_db.py --verify         # build, then re-roll the example
                                                    # waist+prefix+suffix from the DB and
                                                    # compare against the verified SDK output
    python test/build_records_db.py --out records.db --records-dir path/to/records
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from contextlib import closing

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    sys.path.insert(0, HERE)
    from records_api import load_record  # noqa: E402  (used by verify() below)
except ImportError:  # package import (src.gd_save): use the relative module
    from .records_api import load_record

DEFAULT_RECORDS_DIR = os.path.join(HERE, 'records')
DEFAULT_OUT_DB = os.path.join(HERE, 'records.db')

# Only these subfolders of the records tree are converted (the site rolls item stats).
SUBFOLDERS = ('items', 'skills')

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# dbr line parsing
# ---------------------------------------------------------------------------

def parse_line(line):
    """Parse one raw dbr line ('key,value,' / 'key,v1,v2,...,').

    Returns (key, values) where `values` is the list of value texts; a scalar line
    yields a single-element list. Returns (None, None) for blank/comment lines.
    """
    line = line.strip()
    if not line or ',' not in line:
        return None, None
    key, _, rest = line.partition(',')
    key = key.strip()
    if not key:
        return None, None
    parts = rest.split(',')
    # The dbr format ends every line with a comma; drop that single trailing artifact
    # ('key,' -> ['key', ''] -> no values) but keep empty elements in the middle.
    if parts and parts[-1] == '':
        parts = parts[:-1]
    values = [v.strip() for v in parts]
    return key, values


def typed_value(text):
    """Coerce a value text to int / float / str for JSON storage."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def is_empty_value(value):
    """True when a row's effective value is empty (text empty AND value zero).

    Mirrors the exe's input-dump filter (keep iff Value != 0 OR TextValue != ''):
    empty text, and numeric text equal to zero, are both dropped.
    """
    if value is None or value == '':
        return True
    try:
        return float(value) == 0.0
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# schema + build
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE records (
    path    TEXT NOT NULL,   -- 'items/gearaccessories/waist/b202f_waist' (no extension)
    stat    TEXT NOT NULL,   -- field name, e.g. 'characterLife'
    value   TEXT NOT NULL,   -- scalar raw text, or JSON array when is_list = 1
    is_list INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (path, stat)
) WITHOUT ROWID;

CREATE INDEX idx_records_stat ON records(stat);

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;
"""


def build(records_dir, out_db):
    """Convert the dbr tree into out_db. Returns a stats dict."""
    if os.path.exists(out_db):
        os.remove(out_db)

    stats = {
        'files': 0,
        'rows': 0,
        'list_rows': 0,
        'filtered': 0,
        'skip_lines': 0,
    }
    started = time.time()

    conn = sqlite3.connect(out_db)
    try:
        conn.execute('PRAGMA journal_mode = OFF')
        conn.execute('PRAGMA synchronous = OFF')
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.executescript(SCHEMA)

        batch = []
        for sub in SUBFOLDERS:
            root = os.path.join(records_dir, sub)
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in filenames:
                    if not fn.endswith('.dbr'):
                        continue
                    stats['files'] += 1
                    rel = os.path.relpath(os.path.join(dirpath, fn), records_dir)
                    rel = rel.replace('\\', '/')[:-4]  # forward slashes, no extension
                    with open(os.path.join(dirpath, fn), encoding='utf-8-sig', errors='ignore') as fh:
                        for line in fh:
                            key, values = parse_line(line)
                            if key is None:
                                stats['skip_lines'] += 1
                                continue
                            if is_empty_value(values[-1] if len(values) > 1 else values[0]):
                                stats['filtered'] += 1
                                continue
                            if len(values) == 1:
                                batch.append((rel, key, values[0], 0))
                            else:
                                batch.append((rel, key, json.dumps(
                                    [typed_value(v) for v in values]), 1))
                                stats['list_rows'] += 1
                            stats['rows'] += 1
                            if len(batch) >= 100_000:
                                conn.executemany(
                                    'INSERT INTO records(path, stat, value, is_list) '
                                    'VALUES (?, ?, ?, ?)', batch)
                                batch.clear()
        if batch:
            conn.executemany('INSERT INTO records(path, stat, value, is_list) '
                            'VALUES (?, ?, ?, ?)', batch)

        conn.executemany('INSERT INTO meta(key, value) VALUES (?, ?)', [
            ('schema_version', str(SCHEMA_VERSION)),
            ('built_at', time.strftime('%Y-%m-%d %H:%M:%S')),
            ('source_dir', records_dir),
            ('subfolders', ','.join(SUBFOLDERS)),
            ('file_count', str(stats['files'])),
            ('row_count', str(stats['rows'])),
            ('list_row_count', str(stats['list_rows'])),
            ('filtered_row_count', str(stats['filtered'])),
        ])
        conn.commit()
    finally:
        conn.close()

    stats['seconds'] = round(time.time() - started, 1)
    return stats


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------

# The expected output was generated from the author's JSON dump, whose tool float32-
# rounded every numeric value it wrote. The DB stores the exact dbr text, so a roll can
# differ by float32 rounding on individual values (e.g. dbr '-0.040000' vs dump
# '-0.03999999910593033'); numeric comparisons use this epsilon.
_EPS = 1e-6


def _same(a, b):
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) <= _EPS * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return False


def verify(out_db):
    """Re-roll every cross-check combo from DB-loaded records and diff against the
    previously verified SDK output (output_python.json, itself cross-checked against
    the original JS SDK and the author's exe). Numeric values compare with a float32
    epsilon; text fields must match exactly."""
    sys.path.insert(0, os.path.dirname(HERE))
    from gd_item_stats import calculate  # noqa: E402

    spec_file = os.path.join(HERE, 'gd_item_stats', 'cross_check_spec.json')
    with open(spec_file, encoding='utf-8') as fh:
        spec = json.load(fh)
    combos = {c['label']: c for c in spec['combos']}

    expected_file = os.path.join(HERE, 'gd_item_stats', 'output_python.json')
    with open(expected_file, encoding='utf-8') as fh:
        expected = json.load(fh)

    conn = sqlite3.connect(out_db)
    with closing(conn):
        for combo in expected:
            paths = combos[combo['label']]
            base = load_record(conn, paths['base'])
            prefix = load_record(conn, paths['prefix']) if paths['prefix'] else None
            suffix = load_record(conn, paths['suffix']) if paths['suffix'] else None
            got = calculate(base, prefix, suffix, combo['seed'])
            exp = combo['entries']
            if len(got) != len(exp) or any(
                    g['field'] != e['field'] or not _same(g['value'], e['value'])
                    for g, e in zip(got, exp)):
                print(f"MISMATCH {combo['label']} seed {combo['seed']}:")
                for g, e in zip(got, exp):
                    if g['field'] != e['field'] or not _same(g['value'], e['value']):
                        print(f"  got {g}")
                        print(f"  exp {e}")
                if len(got) != len(exp):
                    print(f'  {len(got)} got vs {len(exp)} expected entries')
                return False
            print(f"PASS {combo['label']} seed {combo['seed']} "
                f"({len(got)} entries)")
    return True


def main():
    parser = argparse.ArgumentParser(description='Build the records SQLite database')
    parser.add_argument('--records-dir', default=DEFAULT_RECORDS_DIR,
                        help='directory of raw .dbr dumps (default: test/records)')
    parser.add_argument('--out', default=DEFAULT_OUT_DB,
                        help='output database path (default: test/records.db)')
    parser.add_argument('--verify', action='store_true',
                        help='re-roll the example combo from the built DB and diff '
                            'against the verified SDK output')
    parser.add_argument('--verify-only', action='store_true',
                        help='skip the build; only run --verify against an existing DB')
    args = parser.parse_args()

    if args.verify_only:
        if verify(args.out):
            print('Verification: ALL COMBOS PASS')
        else:
            print('Verification: FAILED')
            sys.exit(1)
        return

    stats = build(args.records_dir, args.out)
    db_size = os.path.getsize(args.out) / 1024 / 1024
    print(f"Built {args.out}")
    print(f"  files     : {stats['files']}")
    print(f"  rows      : {stats['rows']:,}  (of which {stats['list_rows']:,} list rows)")
    print(f"  filtered  : {stats['filtered']:,} empty/zero-value rows dropped")
    print(f"  skipped   : {stats['skip_lines']:,} blank/comment lines")
    print(f"  size      : {db_size:.1f} MB in {stats['seconds']}s")

    if args.verify:
        if verify(args.out):
            print('\nVerification: ALL COMBOS PASS')
        else:
            print('\nVerification: FAILED')
            sys.exit(1)


if __name__ == '__main__':
    main()
