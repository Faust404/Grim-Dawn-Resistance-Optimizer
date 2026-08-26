#!/usr/bin/env python3
"""Accumulate the character's resist stats from a processed save via the DB.

Shipped copy of the test/ pipeline. get_character_resists() is the library
entry point used by the web app's save upload (src/gd_save package); main()
is the file-based CLI used for regeneration in the test sandbox.

Accumulates every stat the character has, summed across sources by stat name:
  1. equipped items — the base record's plain values plus the prefix/suffix
     (affix) records and the ascendant record, all read from the DB without
     any seed rolling; the component and augment records are read plainly
     and added as well. Parts carrying itemSkillName grant a skill: that
     skill's record (following buffSkillName when present) contributes its
     stats only when it is a passive toggle — no skillManaCost and a
     characterManaLimitReserve.
  2. skills — each skill's record indexed at its level (plus any augmentAllLevel
     bonus from equipped items): a level-10 skill takes the
     9th element (zero-indexed) of every list row; scalar rows pass through.
  3. devotions — each devotion's record is read as-is (no rolling, no indexing).

Numeric values with the same stat name add up (defensiveAether 30 + 40 = 70);
non-numeric values keep the first occurrence. Integral results are returned as
ints. Only the KEEP list below is returned; everything else is dropped, with
absent stats zero-filled so every key is always present.

Usage: python src/gd_save/get_character_resists.py
"""
import json
import os
import sqlite3

try:
    from .records_api import load_record, load_record_lists
except ImportError:  # bare-script run: python src/gd_save/get_character_resists.py
    from records_api import load_record, load_record_lists

HERE = os.path.dirname(os.path.abspath(__file__))
SAVE = os.path.join(HERE, 'processed_save.json')
OUT = os.path.join(HERE, 'character_stats.json')
DB = os.path.join(HERE, 'records.db')

resists_list = [
        'defensiveFire', 'defensiveCold', 'defensiveLightning',
        'defensiveElementalResistance', 'defensivePoison', 'defensivePierce',
        'defensiveBleeding', 'defensiveLife', 'defensiveAether', 'defensiveChaos',
    ]

# Stats the equipment gates accumulate on top of the resists: armor
# absorption. Skills and devotions accumulate every stat unconditionally and
# the KEEP filter decides what is surfaced; only the item loops and the
# passive-qualification check gate on this list. Kept out of resists_list so
# the enemy-facing negative-value filter never applies to it.
tracked_stats = resists_list + ['defensiveAbsorptionModifier']

# Only these stats are surfaced to the website; everything else is dropped.
KEEP = [
    'defensiveFire', 'defensiveCold', 'defensiveLightning',
    'defensiveElementalResistance', 'defensivePoison', 'defensivePierce',
    'defensiveBleeding', 'defensiveLife', 'defensiveAether', 'defensiveChaos',
    'defensiveAbsorptionModifier',
]

# Difficulty resistance penalties, keyed by the save's greatestDifficulty
# (Normal / Elite / Ultimate from block 1). Elite penalizes only Fire / Cold /
# Lightning / Poison & Acid / Pierce by −25%; Bleeding / Vitality / Aether /
# Chaos take their first (−25%) penalty on Ultimate, where the other five
# double to −50%. Physical is never penalized and the elemental value is
# folded into the three elemental resists by the caller, so neither appears
# here.
DIFFICULTY_PENALTIES = {
    'Elite': {
        'defensiveFire': -25, 'defensiveCold': -25, 'defensiveLightning': -25,
        'defensivePoison': -25, 'defensivePierce': -25,
    },
    'Ultimate': {
        'defensiveFire': -50, 'defensiveCold': -50, 'defensiveLightning': -50,
        'defensivePoison': -50, 'defensivePierce': -50,
        'defensiveBleeding': -25, 'defensiveLife': -25,
        'defensiveAether': -25, 'defensiveChaos': -25,
    },
}

def add_item_skill_stats(conn, owner_path, part_path, add, source):
    """Add the stats of a skill granted by an item part's itemSkillName row.

    Active skills are excluded: the skill record must have no skillManaCost.
    Passives qualify when they carry characterManaLimitReserve (the
    passive-toggle marker) OR when they grant any of the resists_list stats —
    a passive with neither but real resist contributions is included too.
    When the skill record points at a buffSkillName record, the buff record's
    stats are the ones extracted.
    """
    part = load_record(conn, part_path)
    skill_path = part.get('itemSkillName')
    if not skill_path:
        return
    skill = load_record(conn, skill_path) or {}
    buff = skill.get('buffSkillName')
    if buff:
        skill = load_record(conn, buff) or {}
    if 'skillManaCost' in skill:
        return  # active skill (costs mana to use)
    if 'characterManaLimitReserve' not in skill and not any(
            stat in tracked_stats for stat in skill):
        return  # neither a passive toggle nor a resist/absorption source
    for stat, value in skill.items():
        if stat in resists_list:
            try:
                if float(value) < 0:
                    continue  # enemy-facing resist reduction, not a resist
            except (TypeError, ValueError):
                pass
            # print(owner_path, skill_path, stat, value)
        add(stat, value, source)

def get_character_resists(conn, save):
    """Accumulate the resist stats of a processed save via the records DB and
    return the KEEP-filtered dict (all 11 keys, zero-filled, integral floats
    coerced to int)."""
    stats = {}
    sources = {'equipped': 0, 'component_augment': 0, 'item_skills': 0,
               'skills': 0, 'devotions': 0}

    def add(stat, value, source):
        sources[source] += 1
        try:
            num = float(value)
        except (TypeError, ValueError):
            stats.setdefault(stat, value)
            return
        cur = stats.get(stat)
        if isinstance(cur, str):
            return  # stat already carries a text value; keep the first
        stats[stat] = (cur if isinstance(cur, (int, float)) else 0.0) + num

    # 1. equipped items: base record values (no seed rolling) + affix
    #    (prefix/suffix) + ascendant records read plainly + component/augment
    #    retrieval
    for item in save.get('equipped', []):
        base = load_record(conn, item['base'])
        for stat, value in base.items():
            if stat in tracked_stats:
                # print(item['base'], stat, value)
                add(stat, value, 'equipped')
        add_item_skill_stats(conn, item['base'], item['base'], add, 'item_skills')
        for part in (item.get('prefix'), item.get('suffix')):
            if not part:
                continue
            for stat, value in load_record(conn, part).items():
                if stat in tracked_stats:
                    # print(item['base'], part, stat, value)
                    add(stat, value, 'equipped')
            add_item_skill_stats(conn, item['base'], part, add, 'item_skills')
        asc = item.get('ascendant')
        if asc:
            for stat, value in load_record(conn, asc).items():
                if stat.startswith(('augmentSkill', 'augmentMastery')):
                    continue  # skill/mastery grant rows are not item stats
                if stat in tracked_stats:
                    # print(item['base'], asc, stat, value)
                    add(stat, value, 'equipped')
            add_item_skill_stats(conn, item['base'], asc, add, 'item_skills')
        for part in (item.get('component'), item.get('augment')):
            if not part:
                continue
            for stat, value in load_record(conn, part).items():
                if stat in tracked_stats:
                    # print(item['base'], part, stat, value)
                    add(stat, value, 'component_augment')
            add_item_skill_stats(conn, item['base'], part, add, 'item_skills')

    # 2. skills: level-indexed records (level 10 -> list[9]); a skill that
    #    costs mana is an active skill, not a passive source, so skip it.
    #    augmentAllLevel (+N to all skills) was already folded into the save's
    #    levels by process_save.py, so no extra bonus is added here.
    #    Pet modifier skills are indirection records: their stats live on the
    #    record named by petSkillName, which may in turn point (buffSkillName)
    #    at the actual buff record carrying them.
    for skill in save.get('skills', []):
        level = skill.get('level', 0)
        if level <= 0:
            continue
        rec = load_record_lists(conn, skill['path'])
        if 'petSkillName' in rec:
            rec = load_record_lists(conn, rec['petSkillName'])
            if 'buffSkillName' in rec:
                rec = load_record_lists(conn, rec['buffSkillName'])
            if 'isPetBonusScaling' in rec:
                continue  # pet-only bonuses (pet modifiers) don't reach the player
        if 'skillManaCost' in rec:
            continue
        for stat, value in rec.items():
            if isinstance(value, list):
                if not value:
                    continue
                value = value[min(level - 1, len(value) - 1)]
            if stat in resists_list:
                try:
                    if float(value) < 0:
                        continue  # enemy-facing resist reduction, not a resist
                except (TypeError, ValueError):
                    pass
                # print(skill['name'], stat, value)
                add(stat, value, 'skills')

    # 3. devotions: records as-is
    for devotion in save.get('devotions', []):
        for stat, value in load_record(conn, devotion['path']).items():
            if stat in resists_list:
                # print(devotion['name'], stat, value)
                add(stat, value, 'devotions')

    out = {}
    for k in KEEP:
        v = stats.get(k, 0)
        out[k] = int(v) if isinstance(v, float) and v.is_integer() else v

    # Difficulty penalty on the resist totals (Normal has none). The penalty
    # is a flat subtraction, so it combines with the elemental fold in the
    # caller regardless of ordering.
    for key, penalty in DIFFICULTY_PENALTIES.get(
            save.get('greatestDifficulty'), {}).items():
        v = out.get(key)
        if isinstance(v, (int, float)):
            out[key] = v + penalty
    return out

def main():
    with open(SAVE, encoding='utf-8') as fh:
        save = json.load(fh)
    conn = sqlite3.connect(DB)
    try:
        out = get_character_resists(conn, save)
    finally:
        conn.close()

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=2)

    print(f'Wrote {OUT}')
    print(f'  {len(out)} of {len(save)} keys kept')


if __name__ == '__main__':
    main()
