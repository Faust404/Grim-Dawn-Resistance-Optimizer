#!/usr/bin/env python3
"""Process a parsed save in memory: skill bonuses, arithmetic check, cleanup.

Shipped copy of the test/ pipeline. process_save() is the library entry point
used by the web app's save upload (src/gd_save package); main() is the
file-based CLI used for regeneration in the test sandbox.

Pipeline:
1. apply_equipment_skill_bonuses — increment skill levels by every augment grant
    from the equipped items' base/prefix/suffix and from active set bonuses.
2. check_skill_arithmetic — assert every skill's level equals its original
    level plus the grants it received; raises ValueError on any mismatch.
3. remove_inactive_entries — drop skills/devotions with status 'inactive' to
    reduce bloat, then exclude devotions carrying non-zero experience.

Usage: python src/gd_save/process_save.py
"""
import json
import os
import sqlite3

try:
    from .records_api import apply_equipment_skill_bonuses, remove_inactive_entries
except ImportError:  # bare-script run: python src/gd_save/process_save.py
    from records_api import apply_equipment_skill_bonuses, remove_inactive_entries

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'parsed_save.json')
OUT = os.path.join(HERE, 'processed_save.json')
DB = os.path.join(HERE, 'records.db')


def _norm(p):
    rel = p[len('records/'):] if p.startswith('records/') else p
    rel = rel[:-4] if rel.endswith('.dbr') else rel
    return rel.replace('\\', '/')


def check_skill_arithmetic(changes, orig_level):
    """Assert final == original + bonus per skill; raise ValueError on mismatch."""
    agg = {}
    for c in changes:
        d = agg.setdefault(c['path'], {'bonus': 0, 'final': c['level']})
        d['bonus'] += c['bonus']
        d['final'] = c['level']
    bad = []
    for path, d in agg.items():
        o = orig_level.get(_norm(path))
        ok = d['final'] == (o + d['bonus'] if o is not None else d['bonus'])
        if not ok:
            bad.append((path, o, d['bonus'], d['final']))
    if bad:
        print('Skill bonus arithmetic MISMATCH:')
        for path, o, bonus, final in bad:
            print(f'  {path}: orig={o} bonus={bonus} final={final}')
        # Raise, never sys.exit — a worker-level exit would silently kill a
        # gunicorn worker mid-request.
        raise ValueError('Skill bonus arithmetic MISMATCH: '
                         + '; '.join(f'{p}: orig={o} bonus={b} final={f}'
                                     for p, o, b, f in bad))


def process_save(conn, save):
    """Mutate a parsed save in place: skill bonuses, arithmetic check (raises
    ValueError on mismatch), inactive-entry cleanup, non-zero-experience
    devotion drop. Returns a diagnostics dict with 'changes' (the list of
    {path, bonus, level} applications), 'removed', 'exp_removed' and
    'total_bonus'."""
    orig_level = {_norm(s['path']): s['level'] for s in save['skills']}
    changes = apply_equipment_skill_bonuses(conn, save)
    check_skill_arithmetic(changes, orig_level)
    removed = remove_inactive_entries(save)
    exp_removed = 0
    devotions = save.get('devotions')
    if devotions is not None:
        kept = [d for d in devotions if d.get('experience', 0) == 0]
        exp_removed = len(devotions) - len(kept)
        save['devotions'] = kept
    return {'changes': changes, 'removed': removed,
            'exp_removed': exp_removed,
            'total_bonus': sum(c['bonus'] for c in changes)}


def main():
    with open(SRC, encoding='utf-8') as fh:
        save = json.load(fh)

    conn = sqlite3.connect(DB)
    try:
        result = process_save(conn, save)
    finally:
        conn.close()

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(save, fh, indent=2)

    print(f'Wrote {OUT}')
    print(f'  skill bonuses applied: {len(result["changes"])} applications, '
        f'{result["total_bonus"]} levels granted')
    for section, n in result['removed'].items():
        print(f'  {section}: {n} inactive entries removed '
        f'({len(save[section])} kept)')
    if result['exp_removed']:
        print(f'  devotions: {result["exp_removed"]} non-zero-experience entries '
        f'removed ({len(save.get("devotions", []))} kept)')


if __name__ == '__main__':
    main()
