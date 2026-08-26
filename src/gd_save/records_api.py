#!/usr/bin/env python3
"""Post-DB retrieval API for the records SQLite database (built by build_records_db.py).

Everything read out of test/records.db after the build lives here — the website's
data layer:

  * load_record()                — one record into the flat field -> value map the
                                   item-stats engine rolls with
  * set_bonuses()                — resolve the active set bonuses for equipped items
  * apply_equipment_skill_bonuses() — increment a parsed save's skill levels by the
                                   augment bonuses its equipment grants

All functions take a sqlite3 connection to the records database. Paths may be given
with or without the 'records/' root and the .dbr/.json extension.
"""

import json
import re


def load_record(conn, path):
    """Load one record into the flat field -> value map the SDK engine expects.

    `path` may include the leading 'records/' root ('records/items/.../x') or not
    ('items/.../x'); the extension (.dbr/.json) is optional. Multi-value (tiered)
    fields collapse to their last element — the tier value the game's tooling resolves
    a list to. The DB is already filtered of empty/zero rows at build time, so the map
    rolls byte-identically to the exe.
    """
    rel = path[len('records/'):] if path.startswith('records/') else path
    rel = rel[:-4] if rel.endswith('.dbr') or rel.endswith('.json') else rel
    rel = rel.replace('\\', '/')
    rows = conn.execute(
        'SELECT stat, value, is_list FROM records WHERE path = ?', (rel,)).fetchall()
    fields = {}
    for stat, value, is_list in rows:
        if is_list:
            arr = json.loads(value)
            fields[stat] = arr[-1] if arr else ''
        else:
            fields[stat] = value
    return fields


def load_record_lists(conn, path):
    """Load one record with its multi-value (tiered) rows kept as lists.

    Unlike load_record(), list rows are NOT collapsed to their last element — the
    caller indexes them by skill level (arr[level - 1]) or by set tier. Scalar rows
    return their raw value text. Same path normalization as load_record().
    """
    rel = path[len('records/'):] if path.startswith('records/') else path
    rel = rel[:-4] if rel.endswith('.dbr') or rel.endswith('.json') else rel
    rel = rel.replace('\\', '/')
    rows = conn.execute(
        'SELECT stat, value, is_list FROM records WHERE path = ?', (rel,)).fetchall()
    fields = {}
    for stat, value, is_list in rows:
        fields[stat] = json.loads(value) if is_list else value
    return fields


def set_bonuses(conn, item_paths):
    """Resolve the active set bonuses for a collection of equipped item paths.

    For every itemset at least one input item belongs to (its record has an
    itemSetName row): count how many of the set's members (setMembers list) are among
    the inputs, then resolve the itemset's stats for that tier — list rows return
    element index matched-1 (the game's tier mechanic: [0, 0, 1500, 1500] with 3/4
    pieces gives 1500), scalar rows pass through. Every augment*LevelN row is
    guaranteed its augment*NameN sibling (the skill/mastery that tier grants), so the
    result is self-describing even if the caller filters zero-valued rows. One result
    per itemset regardless of how many of its pieces are equipped.

    Returns a list of {set, matched, members, stats} dicts.
    """
    def norm(p):
        rel = p[len('records/'):] if p.startswith('records/') else p
        rel = rel[:-4] if rel.endswith('.dbr') or rel.endswith('.json') else rel
        return rel.replace('\\', '/')

    items = {norm(p) for p in item_paths}
    if not items:
        return []

    qmarks = ','.join('?' * len(items))
    set_paths = sorted({v for (_p, v) in conn.execute(
        f"SELECT path, value FROM records WHERE stat = 'itemSetName' "
        f"AND path IN ({qmarks})", sorted(items)).fetchall()})
    if not set_paths:
        return []

    results = []
    for set_path in (norm(p) for p in set_paths):
        rows = conn.execute(
            'SELECT stat, value, is_list FROM records WHERE path = ?',
            (set_path,)).fetchall()
        rec = {stat: (value, is_list) for stat, value, is_list in rows}
        members_value, is_list = rec.get('setMembers', (None, 0))
        members = [norm(m) for m in json.loads(members_value)] if is_list else []
        matched = sum(1 for m in members if m in items)
        if matched == 0:
            continue
        stats = {}
        for stat, (value, list_) in rec.items():
            if stat == 'setMembers':
                continue
            if list_:
                arr = json.loads(value)
                stats[stat] = arr[min(matched - 1, len(arr) - 1)]
            else:
                stats[stat] = value
        # Guarantee pairing: every augment*LevelN row carries its augment*NameN
        # sibling (the skill/mastery the tier grant levels), so a resolved tier is
        # self-describing even if the caller filters zero-valued rows afterwards.
        for stat, (value, list_) in rec.items():
            m = re.match(r'^(augment\w+)Level(\d+)$', stat)
            if m and m.group(0) in stats:
                stats.setdefault(m.group(1) + 'Name' + m.group(2), value)
        results.append({
            'set': set_path,
            'matched': matched,
            'members': len(members),
            'stats': stats,
        })
    return results


def apply_equipment_skill_bonuses(conn, save):
    """Increment the skill levels of a parsed save by the augment bonuses its
    equipment grants. No item rolling — plain DB retrieval of the augment rows.

    Grants come from two sources, applied on top of each other:
      * each equipped item's base / prefix / suffix / relic_completion_bonus (the
        relic slot's completion-relic record, empty on every other slot), scanned
        for augment rows:
        augmentSkillLevelN + augmentSkillNameN — the named skill (a record path)
            gains +augmentSkillLevelN.
        augmentMasteryLevelN + augmentMasteryNameN — the named mastery training
            record's class tree (its '_classtraining_' sibling file replaced with
            '_classtree_') contributes every skillNameN entry it lists, each gaining
            +augmentMasteryLevelN.
        augmentAllLevel — a scalar, global +N to every skill the character has
            (every skill present in the save, all classes). Item parts carry it
            directly; set bonuses carry it tier-gated, already resolved to the
            tier's value by set_bonuses().
      * every active set bonus among the equipped bases (see set_bonuses()): the
        resolved tier's augment rows apply exactly the same way, and a set bonus is
        granted once per itemset, not once per equipped set piece.

    save['skills'] entries are matched by normalized path and mutated in place; skills
    granted but not present in the save are appended as inactive entries. Returns the
    list of {path, bonus, level} applications for reporting.
    """
    def _norm(p):
        rel = p[len('records/'):] if p.startswith('records/') else p
        rel = rel[:-4] if rel.endswith('.dbr') else rel
        return rel.replace('\\', '/')

    skills = {_norm(s['path']): s for s in save.get('skills', [])}
    changes = []

    def inc(skill_path, amount):
        rel = _norm(skill_path)
        entry = skills.get(rel)
        if entry is None:
            entry = {'name': rel.rsplit('/', 1)[-1], 'path': skill_path,
                     'level': 0, 'status': 'inactive', 'is_enabled': False,
                     'is_active': False, 'experience': 0}
            skills[rel] = entry
            save['skills'].append(entry)
        entry['level'] += amount
        changes.append({'path': skill_path, 'bonus': amount, 'level': entry['level']})

    def apply(stats):
        """Apply every augment grant in a resolved field map (item part or itemset)."""
        all_level = stats.get('augmentAllLevel')
        if all_level:
            try:
                amount = int(float(all_level))
            except (TypeError, ValueError):
                amount = 0
            if amount > 0:
                for skill in tuple(save.get('skills', [])):
                    inc(skill['path'], amount)
        for key, val in stats.items():
            m = re.match(r'^(augmentSkill|augmentMastery)Level(\d+)$', key)
            if not m:
                continue
            try:
                level = int(float(val))
            except (TypeError, ValueError):
                continue
            if level <= 0:
                continue
            name_path = stats.get(f'{m.group(1)}Name{m.group(2)}')
            if not name_path:
                continue
            if m.group(1) == 'augmentSkill':
                inc(name_path, level)
            else:  # augmentMastery: every skill of the named class's tree
                tree_path = re.sub(r'_classtraining_', '_classtree_', name_path)
                tree_stats = load_record(conn, tree_path)
                for stat, skill_path in (tree_stats or {}).items():
                    if re.match(r'^skillName\d+$', stat):
                        inc(skill_path, level)

    for item in save.get('equipped', []):
        parts = (item.get('base'), item.get('prefix') or '', item.get('suffix') or '',
                 item.get('relic_completion_bonus') or '')
        for part in parts:
            if not part:
                continue
            apply(load_record(conn, part))

    # Set bonuses: resolved once per itemset the equipped bases belong to, so a 4-piece
    # set grants its tier once, not once per piece worn.
    bases = [item['base'] for item in save.get('equipped', []) if item.get('base')]
    for sb in set_bonuses(conn, bases):
        apply(sb['stats'])
    return changes


def remove_inactive_entries(save):
    """Drop every skill and devotion whose status is 'inactive' from a parsed save.

    Mutates save in place, keeping only what the build actually uses — shrinks the
    file and the sections the website iterates. Returns {section: removed_count} for
    the sections that exist in the save.
    """
    removed = {}
    for section in ('skills', 'devotions'):
        entries = save.get(section)
        if entries is None:
            continue
        kept = [e for e in entries if e.get('status') != 'inactive']
        removed[section] = len(entries) - len(kept)
        save[section] = kept
    return removed
