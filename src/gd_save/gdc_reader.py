"""Parser for Grim Dawn character save files (``player.gdc``).

Grim Dawn save files use a simple stream cipher: a 256-entry lookup table is
derived from a per-file seed (stored as the first 4 bytes, XORed with a fixed
constant), and every 4-byte "int" or single byte in the file is XORed against
a running key that evolves as bytes are consumed. Strings are length-prefixed
(int length + that many bytes) and decoded one byte at a time. The file is
organized as a small fixed header followed by a sequence of length-prefixed
"blocks", each of which ends with a 4-byte plaintext checksum that must equal
the cipher key's state at that point -- this makes it possible to verify that
a block was decoded/parsed correctly.

This module decodes the pieces needed to answer "what does the character have
equipped, what skills/devotions are allocated, what the faction
reputations are and the character's progression": block 1 (greatest completed
difficulty), block 3 (equipment), block 8 (skills/devotions) and block 13
(faction reputation). All other blocks are skipped.
"""

import pathlib
import re
import struct
import sys
from typing import Any, Dict

GDC_MAGIC = 0x58434447  # File signature identifying a Grim Dawn character save.

SLOT_ORDER = [
    'head', 'amulet', 'chest', 'legs', 'feet', 'hands',
    'ring1', 'ring2', 'waist', 'shoulders', 'medal', 'relic',
]

SLOT_CAPS = {
    'head':      {'aug': True,  'comp': True},
    'amulet':    {'aug': True,  'comp': True},
    'chest':     {'aug': True,  'comp': True},
    'legs':      {'aug': True,  'comp': True},
    'feet':      {'aug': True,  'comp': True},
    'hands':     {'aug': True,  'comp': True},
    'ring1':     {'aug': True,  'comp': True},
    'ring2':     {'aug': True,  'comp': True},
    'waist':     {'aug': True,  'comp': True},
    'shoulders': {'aug': True,  'comp': True},
    'mainhand':  {'aug': True,  'comp': True},
    'offhand':   {'aug': True,  'comp': True},
    'medal':     {'aug': False, 'comp': True},
    'relic':     {'aug': False, 'comp': False},
}

# Faction reputation block (13) entry layout: 1 + 1 + 4 + 4 + 4 bytes.
FACTION_ENTRY_BYTES = 14

# Block 1 greatest_difficulty_completed byte -> in-game difficulty name.
# The byte is 0 Normal, 1 Elite, 2 Ultimate (Veteran is a challenge bit on
# Normal and does not affect it).
DIFFICULTY_NAMES = {
    0: 'Normal',
    1: 'Elite',
    2: 'Ultimate',
}


def short_name(path: str) -> str:
    """Strip a records/.../Foo.dbr path down to just 'Foo'."""
    if not path:
        return ''
    path = path.replace('\\', '/')
    return re.sub(r'^.*/|\.dbr$', '', path, flags=re.IGNORECASE)


def faction_tier(value: float) -> str:
    """Map a raw faction reputation value to its in-game tier name.

    Tiers are positive thresholds; any negative value is a hostile tier and
    is lumped together as "Hostile" (the save stores no tier/name info).
    """
    if value >= 25000:
        return 'Revered'
    if value >= 10001:
        return 'Honored'
    if value >= 5001:
        return 'Respected'
    if value >= 1501:
        return 'Friendly'
    if value >= 0:
        return 'Neutral'
    return 'Hostile'


# Save-slot → faction name. The save stores only the slot id; the mapping
# comes from records/game/gamefactions.dbr plus each faction controller's
# `myFaction` field (test/records/controllers/factions/*.dbr): the fixed
# slugs are Survivors → slot 1 and Drifters ("User0") → slot 6, then
# factionUser<N> occupies slot N + 6. Record filenames are NOT reliable
# display names: factiongdx3_avian.dbr (User21 → slot 27) is the Noktukari
# faction ("Avian" is only the internal codename — its NPCs are "Elder
# Noktukari" and the area-H blacksmith "Noktukari", achievement
# AREAH_NOKTUKARI_MET), while factiongdx2_eldritch.dbr (User16 → slot 22)
# is the Eldritch kill-faction, which we don't surface. Only the factions
# shown in the web app are listed here.
FACTION_SLOTS = {
    1: "Devil's Crossing",
    6: 'Rovers',
    8: 'Homestead',
    10: 'The Outcast',
    11: "Order of Death's Vigil",
    13: 'The Black Legion',
    14: "Kymon's Chosen",
    15: 'Coven of Ugdenbog',
    16: 'Barrowholm',
    17: 'Malmouth Resistance',
    19: 'Cult of Bysmiel',
    20: 'Cult of Dreeg',
    21: 'Cult of Solael',
    23: 'Kurn',
    27: 'Noktukari',
}


class GdcReader:
    """Stateful cursor over a decrypted .gdc byte stream."""

    def __init__(self, data: bytes):
        self.buf = data
        self.len = len(data)
        self.pos = 0

        if self.len < 32:
            raise ValueError('Save file is too short.')

        seed = (self.u32_at(0) ^ 0x55555555) & 0xFFFFFFFF
        self.key = seed
        self.seed = seed
        self.pos = 4

        # Build the per-file substitution table used to evolve the cipher
        # key as each byte is consumed.
        self.table = [0] * 256
        k = seed
        for i in range(256):
            k = ((k >> 1) | ((k & 1) << 31)) & 0xFFFFFFFF
            k = (k * 39916801) & 0xFFFFFFFF
            self.table[i] = k

        self.data_version = 0

    # -- low-level primitives ------------------------------------------------

    def u32_at(self, off: int) -> int:
        return struct.unpack_from('<I', self.buf, off)[0]

    def read_int(self) -> int:
        """Read a 4-byte encrypted int, decoded as a single 32-bit XOR."""
        if self.pos + 4 > self.len:
            raise ValueError('Read past end of file (int).')
        enc = self.u32_at(self.pos)
        val = (enc ^ self.key) & 0xFFFFFFFF
        for i in range(4):
            self.key = (self.key ^ self.table[self.buf[self.pos + i]]) & 0xFFFFFFFF
        self.pos += 4
        return val

    def read_raw_int(self) -> int:
        """Like read_int, but does not advance the cipher key (used for
        block-length fields, which sit between the block id and the block's
        encrypted payload)."""
        if self.pos + 4 > self.len:
            raise ValueError('Read past end of file (raw int).')
        enc = self.u32_at(self.pos)
        val = (enc ^ self.key) & 0xFFFFFFFF
        self.pos += 4
        return val

    def read_plain_int(self) -> int:
        """Read a 4-byte value with no decryption at all (used for the
        plaintext checksum that terminates every block)."""
        v = self.u32_at(self.pos)
        self.pos += 4
        return v

    def read_byte(self) -> int:
        if self.pos + 1 > self.len:
            raise ValueError('Read past end of file (byte).')
        b = self.buf[self.pos]
        val = b ^ (self.key & 0xFF)
        self.key = (self.key ^ self.table[b]) & 0xFFFFFFFF
        self.pos += 1
        return val

    def read_float(self) -> float:
        """Read a 4-byte encrypted value as a little-endian float32.

        The cipher operates on the raw 4 bytes exactly like read_int; only
        the interpretation of the resulting bit pattern differs.
        """
        if self.pos + 4 > self.len:
            raise ValueError('Read past end of file (float).')
        enc = self.u32_at(self.pos)
        val = (enc ^ self.key) & 0xFFFFFFFF
        for i in range(4):
            self.key = (self.key ^ self.table[self.buf[self.pos + i]]) & 0xFFFFFFFF
        self.pos += 4
        return struct.unpack('<f', struct.pack('<I', val))[0]

    def read_string(self) -> str:
        n = self.read_int()
        if n < 0 or n > 2048 or self.pos + n > self.len:
            raise ValueError(f'Suspicious string length ({n}).')
        return ''.join(chr(self.read_byte()) for _ in range(n))

    def read_wstring(self) -> str:
        n = self.read_int()
        if n < 0 or n > 2048:
            raise ValueError(f'Suspicious wide string length ({n}).')
        out = []
        for _ in range(n):
            lo = self.read_byte()
            hi = self.read_byte()
            out.append(chr(lo | (hi << 8)))
        return ''.join(out)

    def skip_block_body(self, content_start: int, length: int) -> None:
        """Jump past a block we don't care about and resync the cipher key
        against its trailing plaintext checksum."""
        self.pos = content_start + length
        self.key = self.read_plain_int()

    # -- items -----------------------------------------------------------

    def read_item(self, extra_ints: int) -> Dict[str, Any]:
        base = self.read_string()
        prefix = self.read_string()
        suffix = self.read_string()
        modifier = self.read_string()
        transmute = self.read_string()
        seed = self.read_int()

        component = self.read_string()
        relic_completion_bonus = self.read_string()
        relic_seed = self.read_int()
        augment = self.read_string()

        augment_level = self.read_int()
        augment_seed = self.read_int()

        # Save files are always at least version 8, so these fields are
        # always present.
        ascendant = self.read_string()
        ascendant_2h = self.read_string()

        materia_combines = self.read_int()
        stack_count = self.read_int()

        seed_rerolls = self.read_int()
        affix_rerolls = self.read_int()

        attached = self.read_byte() == 1

        for _ in range(extra_ints):
            self.read_int()

        # print(base, ascendant)
        return {
            'base': base,
            'prefix': prefix,
            'suffix': suffix,
            'modifier': modifier,
            'transmute': transmute,
            'seed': seed,
            'component': component,
            'relic_completion_bonus': relic_completion_bonus,
            'relic_seed': relic_seed,
            'augment': augment,
            'augment_level': augment_level,
            'augment_seed': augment_seed,
            'ascendant': ascendant,
            'ascendant_2h': ascendant_2h,
            'materia_combines': materia_combines,
            'stack_count': stack_count,
            'seed_rerolls': seed_rerolls,
            'affix_rerolls': affix_rerolls,
            'attached': attached,
        }

    # -- top-level parse ---------------------------------------------------

    def parse(self) -> Dict[str, Any]:
        magic = self.read_int()
        self.read_int()
        if magic != GDC_MAGIC:
            raise ValueError('Not a Grim Dawn character save file (invalid magic).')

        name = self.read_wstring()
        self.read_byte()
        cls = self.read_string()
        level = self.read_int()
        self.read_byte()
        self.read_byte()

        self.read_plain_int()
        self.data_version = self.read_int()
        for _ in range(16):
            self.read_byte()

        block1 = None
        block3 = None
        block8 = {'skills': [], 'devotions': []}
        block13 = None
        guard = 0

        while self.pos < self.len and guard < 200:
            guard += 1
            block_id = self.read_int()
            length = self.read_raw_int()
            content_start = self.pos

            if length < 0 or content_start + length > self.len:
                raise ValueError(f'Corrupted block frame id={block_id}.')

            if block_id == 1:
                block1 = self.read_block1(content_start, length)
            elif block_id == 3:
                block3 = self.read_block3(content_start, length)
            elif block_id == 8:
                block8 = self.read_block8(content_start, length)
            elif block_id == 13:
                block13 = self.read_block13(content_start, length)
            else:
                self.skip_block_body(content_start, length)

        if block3 is None:
            raise ValueError('Inventory block not found (block id=3).')

        factions = None
        if block13 is not None:
            factions = {'selection': block13['selection'], 'entries': []}
            for idx, e in enumerate(block13['entries']):
                factions['entries'].append({
                    'id': idx,
                    'changed': e['changed'],
                    'unlocked': e['unlocked'],
                    'value': e['value'],
                    'positive_boost': e['positive_boost'],
                    'negative_boost': e['negative_boost'],
                    'tier': faction_tier(e['value']),
                })

        return {
            'character': name,
            'level': level,
            'class': cls,
            'seed': self.seed,
            'greatest_difficulty': (block1 or {}).get('greatest_difficulty'),
            'equipment': block3['equipment'],
            'weapons': block3['weapons'],
            'weaponSet': block3['weaponSet'],
            'skills': block8.get('skills', []),
            'devotions': block8.get('devotions', []),
            'factions': factions,
        }

    # -- block 3: equipment --------------------------------------------------
    #
    # The item struct has a handful of trailing integer fields whose exact
    # count depends on details we haven't fully pinned down, so this tries a
    # small set of candidate counts and keeps whichever one lets the block's
    # payload be consumed exactly and match its trailing checksum.

    def read_block3(self, content_start: int, length: int) -> Dict[str, Any]:
        saved_key = self.key
        candidate_extra_int_counts = [4, 0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 12]

        for extra in candidate_extra_int_counts:
            self.pos = content_start
            self.key = saved_key
            try:
                block = self._try_read_block3(content_start, length, extra)
                self.pos = content_start + length
                self.key = self.read_plain_int()
                return block
            except Exception:
                continue

        raise ValueError('Failed to parse equipment block (unknown item format variant).')

    def _try_read_block3(self, content_start: int, length: int, extra: int) -> Dict[str, Any]:
        expected_end = content_start + length
        self.read_int()
        has_data = self.read_byte()

        equipment = []
        weapons = {'main': None, 'off': None}
        weapon_set = 0

        if has_data == 1:
            sack_count = self.read_int()
            self.read_int()
            self.read_int()

            if sack_count < 0 or sack_count > 64:
                raise ValueError(f'Suspicious sack count ({sack_count}).')

            for _ in range(sack_count):
                self.read_int()
                nlen = self.read_raw_int()
                nstart = self.pos
                if nlen < 0 or nstart + nlen > self.len:
                    raise ValueError('Corrupted equipment sack.')
                self.skip_block_body(nstart, nlen)

            use_alt = self.read_byte()
            weapon_set = use_alt

            for i in range(12):
                it = self.read_item(extra)
                equipment.append({'slot': SLOT_ORDER[i], 'item': it})

            set1 = []
            self.read_byte()
            for _ in range(2):
                set1.append(self.read_item(extra))

            set2 = []
            self.read_byte()
            for _ in range(2):
                set2.append(self.read_item(extra))

            active = set2 if use_alt == 1 else set1
            weapons['main'] = active[0]
            weapons['off'] = active[1]

        if self.pos != expected_end:
            raise ValueError('Block 3 did not consume exact payload length.')

        checksum = self.read_plain_int()
        if checksum != self.key:
            raise ValueError('Block 3 checksum mismatch.')

        return {'equipment': equipment, 'weapons': weapons, 'weaponSet': weapon_set}

    # -- block 8: skills / devotions ------------------------------------------
    #
    # Each entry is:
    #
    #   string   base_name
    #   int      level
    #   byte     enabled
    #   byte     <reserved>
    #   int      devotion_level
    #   int      experience
    #   int      is_active
    #   byte     <reserved>
    #   byte     <reserved>
    #   [optional] string autocast_skill
    #   [optional] string autocast_controller
    #
    # The trailing pair of strings carries item-proc / devotion-proc data
    # (e.g. "grants a chance to cast X on attack") and is only present on
    # some entries, with no explicit flag marking its presence. We resolve
    # that with a one-entry lookahead: tentatively read the two strings and
    # only keep them if doing so leaves the stream aligned on something that
    # still looks like a valid entry -- another "records/....dbr" name, or
    # the end of the block.

    def _peek_string(self):
        """Try to read a length-prefixed string at the current position
        without permanently consuming it. Returns (ok, text)."""
        saved_pos, saved_key = self.pos, self.key
        ok, text = False, None
        try:
            n = self.read_int()
            if 0 <= n <= 300 and self.pos + n <= self.len:
                chars = [self.read_byte() for _ in range(n)]
                text = ''.join(chr(c) for c in chars)
                ok = (n == 0) or all(32 <= c < 127 for c in chars)
        except Exception:
            ok, text = False, None
        self.pos, self.key = saved_pos, saved_key
        return ok, text

    def _looks_like_entry_boundary(self, expected_end: int) -> bool:
        """True if the current position looks like the start of another
        skill entry (or we're at/near the end of the block)."""
        if self.pos >= expected_end - 4:
            return True
        ok, text = self._peek_string()
        if not ok:
            return False
        return text == '' or (text.lower().startswith('records/') and text.lower().endswith('.dbr'))

    def _read_skill_entry(self, expected_end: int) -> Dict[str, Any]:
        name = self.read_string()
        level = self.read_int()
        enabled = self.read_byte() != 0

        self.read_byte()  # reserved

        devotion_level = self.read_int()
        experience = self.read_int()
        is_active = self.read_int() != 0

        self.read_byte()  # reserved
        self.read_byte()  # reserved

        autocast_skill = ''
        autocast_controller = ''
        saved_pos, saved_key = self.pos, self.key
        has_first, _ = self._peek_string()
        if has_first:
            try:
                cand_skill = self.read_string()
                has_second, _ = self._peek_string()
                if has_second:
                    cand_controller = self.read_string()
                    if self._looks_like_entry_boundary(expected_end):
                        autocast_skill = cand_skill
                        autocast_controller = cand_controller
                    else:
                        self.pos, self.key = saved_pos, saved_key
                else:
                    self.pos, self.key = saved_pos, saved_key
            except Exception:
                self.pos, self.key = saved_pos, saved_key

        return {
            'raw_name': name,
            'level': level,
            'is_enabled': enabled,
            'devotion_level': devotion_level,
            'experience': experience,
            'is_active': is_active,
            'autocast_skill': autocast_skill,
            'autocast_controller': autocast_controller,
        }

    def read_block8(self, content_start: int, length: int) -> Dict[str, Any]:
        self.pos = content_start
        try:
            result = self._try_read_block8(content_start, length)
            self.pos = content_start + length
            self.key = self.read_plain_int()
            return result
        except Exception:
            # Save format changed, or this block is genuinely malformed --
            # skip it rather than raising, so the rest of the save can
            # still be parsed. skip_block_body resyncs pos/key regardless
            # of how far _try_read_block8 got before failing.
            self.skip_block_body(content_start, length)
            return {'skills': [], 'devotions': []}

    def _try_read_block8(self, content_start: int, length: int) -> Dict[str, Any]:
        expected_end = content_start + length
        self.read_int()  # block version (unused: entry layout is fixed)
        num_skills = self.read_int()

        if num_skills < 0 or num_skills > 10000:
            raise ValueError(f'Suspicious skill count ({num_skills}).')

        skills = []
        devotions = []

        for _ in range(num_skills):
            entry = self._read_skill_entry(expected_end)

            level = entry['level']
            dev_level = entry['devotion_level']
            enabled = entry['is_enabled']
            is_act = entry['is_active']

            if level <= 0 and dev_level <= 0 and not enabled:
                continue

            norm_path = entry['raw_name'].replace('\\', '/')
            is_devotion = (
                'devotion' in norm_path.lower()
                or 'shrine' in norm_path.lower()
                or dev_level > 0
            )

            formatted = {
                'name': short_name(entry['raw_name']),
                'path': norm_path,
                'level': level,
                'status': 'active' if (enabled or is_act) else 'inactive',
                'is_enabled': enabled,
                'is_active': is_act,
                'experience': entry['experience'],
            }
            if entry['autocast_skill']:
                formatted['autocast_skill'] = short_name(entry['autocast_skill'])
            if entry['autocast_controller']:
                formatted['autocast_controller'] = short_name(entry['autocast_controller'])

            if is_devotion:
                formatted['devotion_level'] = dev_level
                devotions.append(formatted)
            else:
                skills.append(formatted)

        # Drain any trailing block metadata bytes to align stream cipher key with checksum
        while self.pos < expected_end:
            self.read_byte()

        checksum = self.read_plain_int()
        if checksum != self.key:
            raise ValueError('Block 8 checksum mismatch.')

        return {'skills': skills, 'devotions': devotions}

    # -- block 13: faction reputation -----------------------------------------
    #
    # Layout (per GDStash, no leading version int unlike blocks 3/8):
    #
    #   int    faction_selection
    #   int    faction_count
    #   count  entries of:
    #     byte  changed
    #     byte  unlocked
    #     float value
    #     float positive_boost
    #     float negative_boost
    #
    # The array index is the faction id (the save stores no names). A few
    # layout candidates are tried -- with/without a leading version int, and
    # count-prefixed vs fixed-size (entries filling the payload) -- and the
    # first one that consumes the payload exactly wins.

    def read_block13(self, content_start: int, length: int) -> Dict[str, Any]:
        saved_key = self.key
        for layout in ('count', 'version_count', 'fixed', 'version_fixed'):
            self.pos = content_start
            self.key = saved_key
            try:
                block = self._try_read_block13(content_start, length, layout)
                self.pos = content_start + length
                self.key = self.read_plain_int()
                print(f'Faction reputation block: layout={layout}, '
                    f'count={len(block["entries"])}', file=sys.stderr)
                return block
            except Exception:
                continue

        raise ValueError('Failed to parse faction reputation block (unknown layout).')

    def _try_read_block13(self, content_start: int, length: int, layout: str) -> Dict[str, Any]:
        expected_end = content_start + length
        if layout.startswith('version'):
            self.read_int()

        selection = self.read_int()
        entries = []

        if layout.endswith('fixed'):
            remaining = expected_end - self.pos
            if remaining < 0 or remaining % FACTION_ENTRY_BYTES != 0:
                raise ValueError('Faction block length not a multiple of entry size.')
            count = remaining // FACTION_ENTRY_BYTES
        else:
            count = self.read_int()
            if count < 0 or count > 512:
                raise ValueError(f'Suspicious faction count ({count}).')

        for _ in range(count):
            entries.append({
                'changed': self.read_byte() == 1,
                'unlocked': self.read_byte() == 1,
                'value': self.read_float(),
                'positive_boost': self.read_float(),
                'negative_boost': self.read_float(),
            })

        if self.pos != expected_end:
            raise ValueError('Faction block did not consume exact payload length.')

        return {'selection': selection, 'entries': entries}


    # -- block 1: character progression -----------------------------------------
    #
    # Layout, version 5 (the only version this reader supports; per
    # Christopher's decryptsave.cc-derived reader and the gdcx library):
    #
    #   int    version              (must be 5)
    #   byte   is_in_main_quest
    #   byte   has_been_in_game
    #   byte   difficulty           (packed byte, see below)
    #   byte   greatest_difficulty_completed
    #   int    iron                 (money)
    #   byte   greatest_survival_completed
    #   int    tributes
    #   byte   compass_state
    #   byte   show_skill_help
    #   byte   weapon_set_active    (IsAltWeaponSet)
    #   byte   weapon_set_enabled   (IsAltWeaponSetEnabled)
    #   string player_texture
    #   int    loot_filter_count
    #   count  loot_filter bytes    (0/1 flags; drained raw)
    #
    # There is no quest/progression flag list in v5 — the "quest flags" of
    # older write-ups belong to earlier block versions. The difficulty byte
    # packs three flags: bits 0-3 difficulty (0 Normal, 1 Elite, 2 Ultimate),
    # bits 4-5 challenge (1 = Veteran on Normal, 3 = Ascended on Ultimate)
    # and bits 6-7 game mode (0 = main game, 1 = Crucible).
    #
    # Every field must be consumed so the payload fits exactly and its
    # trailing plaintext checksum matches the cipher key state, but only the
    # greatest completed difficulty is surfaced (parse_save renders it as
    # Normal / Elite / Ultimate); the rest is not needed right now.
    #
    # Validated like blocks 3/13: the version must be 5, the fields must
    # consume the payload exactly and the trailing plaintext checksum must
    # match the cipher key state.

    def read_block1(self, content_start: int, length: int) -> Dict[str, Any]:
        saved_key = self.key
        self.pos = content_start
        self.key = saved_key
        try:
            block = self._try_read_block1(content_start, length)
            self.pos = content_start + length
            self.key = self.read_plain_int()
            print(f'Progression block: greatest_difficulty={block["greatest_difficulty"]}',
                  file=sys.stderr)
            return block
        except Exception:
            pass

        # Unknown version or corrupt — skip and resync like any other
        # unparsed block, so the rest of the save still parses.
        self.skip_block_body(content_start, length)
        return {'greatest_difficulty': None}

    def _try_read_block1(self, content_start: int, length: int) -> Dict[str, Any]:
        expected_end = content_start + length

        version = self.read_int()
        if version != 5:
            raise ValueError(f'Unsupported block 1 version ({version}).')

        self.read_byte()             # is_in_main_quest
        self.read_byte()             # has_been_in_game
        self.read_byte()             # difficulty (packed byte)
        greatest_difficulty = self.read_byte()
        self.read_int()              # iron (money)
        self.read_byte()             # greatest_survival_completed
        self.read_int()              # tributes
        self.read_byte()             # compass_state
        self.read_byte()             # show_skill_help
        self.read_byte()             # weapon_set_active (IsAltWeaponSet)
        self.read_byte()             # weapon_set_enabled (IsAltWeaponSetEnabled)
        self.read_string()           # player_texture

        loot_count = self.read_int()
        if loot_count < 0 or loot_count > 1000:
            raise ValueError(f'Suspicious loot filter count ({loot_count}).')
        for _ in range(loot_count):
            self.read_byte()

        if self.pos != expected_end:
            raise ValueError('Block 1 did not consume exact payload length.')

        checksum = self.read_plain_int()
        if checksum != self.key:
            raise ValueError('Block 1 checksum mismatch.')

        return {'greatest_difficulty': greatest_difficulty}


def parse_save(file_bytes: bytes) -> Dict[str, Any]:
    save = GdcReader(file_bytes).parse()

    by_slot = {entry['slot']: entry['item'] for entry in save['equipment']}
    main = save['weapons']['main']
    off = save['weapons']['off']

    if main:
        by_slot['mainhand'] = main
    if off:
        by_slot['offhand'] = off

    weapon_mode = '1h'
    if main and not off and re.search(r'/(melee2h|ranged2h)/', main.get('base', ''), re.IGNORECASE):
        weapon_mode = '2h'

    state = {}
    free_comp = 0
    free_aug = 0

    for slot, cap in SLOT_CAPS.items():
        it = by_slot.get(slot)
        has_item = it is not None and bool(it.get('base'))

        comp_free = cap['comp'] and has_item and not bool(it.get('component'))
        aug_free = cap['aug'] and has_item and not bool(it.get('augment'))

        state[slot] = {'aug': aug_free, 'comp': comp_free}

        if comp_free:
            free_comp += 1
        if aug_free:
            free_aug += 1

    equipped = []
    for slot in SLOT_CAPS:
        it = by_slot.get(slot)
        if not it or not it.get('base'):
            continue
        equipped.append({
            'slot': slot,
            'base': it.get('base', '').replace('\\', '/'),
            'prefix': it.get('prefix', '').replace('\\', '/'),
            'suffix': it.get('suffix', '').replace('\\', '/'),
            'ascendant': it.get('ascendant', '').replace('\\', '/'),
            'seed': it.get('seed', 0),
            'component': it.get('component', '').replace('\\', '/'),
            'augment': it.get('augment', '').replace('\\', '/'),
            'relic_completion_bonus': it.get('relic_completion_bonus', '').replace('\\', '/'),
        })

    # Faction standings as a flat {name: tier} dict. Keys use the same
    # faction names as the web backend's player_faction_standings
    # (web/app.py), so a save upload can pre-fill the UI's standing
    # dropdowns; values are the backend's tier strings (Friendly /
    # Respected / Honored / Revered, "Hostile" for negative values).
    # Only the tracked slots (FACTION_SLOTS) are emitted.
    factions = {}
    for e in (save.get('factions') or {}).get('entries', []):
        name = FACTION_SLOTS.get(e['id'])
        if name:
            factions[name] = e['tier']

    return {
        'character': save['character'],
        'level': save['level'],
        'class': save['class'],
        'seed': save.get('seed'),
        # Greatest difficulty this character has completed, as a name
        # (Normal / Elite / Ultimate) — the only block-1 field surfaced for now.
        'greatestDifficulty': DIFFICULTY_NAMES.get(
            save.get('greatest_difficulty') or -1),
        'weaponMode': weapon_mode,
        'state': state,
        'equipped': equipped,
        'skills': save['skills'],
        'devotions': save['devotions'],
        'factions': factions,
        'summary': {'free_comp': free_comp, 'free_aug': free_aug},
    }


if __name__ == '__main__':
    import json

    # Shipped copy: the save path comes from argv (defaults to player.gdc in
    # the CWD); the test/ copy keeps the hardcoded local paths.
    save_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('player.gdc')
    if save_path.exists():
        data = save_path.read_bytes()
        result = parse_save(data)
        print(json.dumps(result, indent=2))
        with open("parsed_save.json", "w") as f:
            json.dump(result, f, indent=2)
    else:
        print(f"Save file not found at: {save_path}")
