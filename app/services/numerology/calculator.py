"""Core Vedic / Lo-Shu numerology calculations."""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


# Chaldean letter values (compound name numerology used in Spiritual Hut reports)
CHALDEAN = {
    "A": 1, "I": 1, "J": 1, "Q": 1, "Y": 1,
    "B": 2, "K": 2, "R": 2,
    "C": 3, "G": 3, "L": 3, "S": 3,
    "D": 4, "M": 4, "T": 4,
    "E": 5, "H": 5, "N": 5, "X": 5,
    "U": 6, "V": 6, "W": 6,
    "O": 7, "Z": 7,
    "F": 8, "P": 8,
}

# Planet / ruler by number 1-9
NUMBER_PLANET = {
    1: ("Sun", "Surya"),
    2: ("Moon", "Chandra"),
    3: ("Jupiter", "Guru"),
    4: ("Rahu", "Rahu"),
    5: ("Mercury", "Budh"),
    6: ("Venus", "Shukra"),
    7: ("Ketu", "Ketu"),
    8: ("Saturn", "Shani"),
    9: ("Mars", "Mangal"),
}

# Friend / enemy / neutral grids by moolank (driver number)
COMPATIBILITY = {
    1: {"friend": [1, 2, 3, 5, 6, 9], "enemy": [8], "neutral": [4, 7]},
    2: {"friend": [1, 2, 3, 5], "enemy": [8, 4, 9], "neutral": [6, 7]},
    3: {"friend": [1, 2, 3, 5, 7, 9], "enemy": [6], "neutral": [4, 8]},
    4: {"friend": [5, 6, 7, 1, 8], "enemy": [2, 9, 4], "neutral": [3]},
    5: {"friend": [1, 2, 3, 5, 6, 7, 8, 9], "enemy": [], "neutral": [4]},
    6: {"friend": [1, 5, 6, 7], "enemy": [3], "neutral": [2, 4, 8, 9]},
    7: {"friend": [1, 3, 4, 5, 6], "enemy": [2, 9], "neutral": [7, 8]},
    8: {"friend": [3, 5, 6, 7], "enemy": [1, 2, 4, 8], "neutral": [9]},
    9: {"friend": [1, 3, 5], "enemy": [4, 2], "neutral": [6, 7, 8, 9]},
}

# Western zodiac by month/day (tropical)
ZODIAC = [
    ((1, 20), "Capricorn", "Saturn"),
    ((2, 19), "Aquarius", "Saturn/Uranus"),
    ((3, 20), "Pisces", "Jupiter/Neptune"),
    ((4, 20), "Aries", "Mars"),
    ((5, 21), "Taurus", "Venus"),
    ((6, 21), "Gemini", "Mercury"),
    ((7, 22), "Cancer", "Moon"),
    ((8, 23), "Leo", "Sun"),
    ((9, 23), "Virgo", "Mercury"),
    ((10, 23), "Libra", "Venus"),
    ((11, 22), "Scorpio", "Mars/Pluto"),
    ((12, 22), "Sagittarius", "Jupiter"),
    ((12, 31), "Capricorn", "Saturn"),
]

# Lo-Shu cell positions (row, col) for digits 1-9
LOSHU_POSITIONS = {
    4: (0, 0), 9: (0, 1), 2: (0, 2),
    3: (1, 0), 5: (1, 1), 7: (1, 2),
    8: (2, 0), 1: (2, 1), 6: (2, 2),
}


def reduce_number(n: int, keep_master: bool = False) -> int:
    """Reduce to single digit. Optionally keep 11/22."""
    while n > 9:
        if keep_master and n in (11, 22):
            return n
        n = sum(int(d) for d in str(n))
    return n


def moolank_from_dob(dob: date) -> int:
    """Driver / psychic / birth number from day of month."""
    return reduce_number(dob.day)


def bhagyank_from_dob(dob: date) -> int:
    """Destiny / conductor number from full DOB digits."""
    digits = f"{dob.day:02d}{dob.month:02d}{dob.year}"
    return reduce_number(sum(int(d) for d in digits))


def compound_day(dob: date) -> int:
    """Unreduced day number (e.g. 25 stays 25 before describing 2+5)."""
    return dob.day


def name_number(name: str) -> Tuple[int, int]:
    """Return (compound_total, reduced) using Chaldean values."""
    total = 0
    for ch in name.upper():
        if ch.isalpha():
            total += CHALDEAN.get(ch, 0)
    return total, reduce_number(total)


def split_name(full_name: str) -> Tuple[str, str, str]:
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", parts[0]
    return parts[0], parts[-1], " ".join(parts)


def zodiac_for_dob(dob: date) -> Tuple[str, str]:
    md = (dob.month, dob.day)
    # Capricorn spans year boundary
    if md >= (12, 22) or md <= (1, 19):
        return "Capricorn", "Saturn"
    prev = ("Capricorn", "Saturn")
    for (m, d), sign, planet in ZODIAC:
        if md <= (m, d):
            return sign, planet
        prev = (sign, planet)
    return prev


def build_loshu_grid(dob: date) -> Dict:
    """Build Lo-Shu grid counts from DOB digits + moolank/bhagyank inclusion rules.

    Digits used: day, month, year digits. Multiples accumulate in cells.
    """
    digits: List[int] = []
    for part in (dob.day, dob.month, dob.year):
        digits.extend(int(d) for d in str(part) if d != "0")

    counts = {i: 0 for i in range(1, 10)}
    for d in digits:
        if 1 <= d <= 9:
            counts[d] += 1

    grid = [["" for _ in range(3)] for _ in range(3)]
    for num, (r, c) in LOSHU_POSITIONS.items():
        grid[r][c] = str(num) * counts[num] if counts[num] else ""

    present = [n for n in range(1, 10) if counts[n] > 0]
    missing = [n for n in range(1, 10) if counts[n] == 0]

    return {
        "counts": counts,
        "grid": grid,
        "present": present,
        "missing": missing,
    }


def mobile_number_total(mobile: str) -> Optional[Tuple[int, int]]:
    digits = [int(c) for c in mobile if c.isdigit()]
    if not digits:
        return None
    total = sum(digits)
    return total, reduce_number(total)


def dasha_numbers(dob: date, as_of: Optional[date] = None) -> Dict:
    """Simple mahadasha cycle based on moolank starting at birth.

    Each number rules for (number) years in the classic psychic-number dasha
    sequence starting from moolank. This is a practical approximation for
    report generation; content copy can refine later.
    """
    as_of = as_of or date.today()
    driver = moolank_from_dob(dob)
    age_days = (as_of - dob).days
    age_years = age_days / 365.25

    # Cycle 1-9 starting at driver
    sequence = [(driver + i - 1) % 9 or 9 for i in range(9)]
    # Each dasha lasts the number of years equal to the number itself
    elapsed = 0.0
    current = sequence[0]
    antar = sequence[0]
    for n in sequence * 20:  # enough cycles for a lifetime
        length = float(n)
        if elapsed + length > age_years:
            current = n
            # antar: split current dasha into 9 sub-periods proportionally
            into = age_years - elapsed
            sub_elapsed = 0.0
            for sn in sequence:
                sub_len = length * (sn / sum(sequence))
                if sub_elapsed + sub_len > into:
                    antar = sn
                    break
                sub_elapsed += sub_len
            break
        elapsed += length

    planet_en, planet_sa = NUMBER_PLANET.get(current, ("", ""))
    return {
        "maha_dasha": current,
        "antar_dasha": antar,
        "pratyantar_dasha": antar,  # placeholder until finer engine
        "maha_planet": planet_en,
        "maha_planet_sa": planet_sa,
    }


def compatibility_score(moolank: int) -> Dict:
    data = COMPATIBILITY.get(moolank, COMPATIBILITY[5])
    friends = data["friend"]
    # Simple score: more friends => higher baseline compatibility vibe
    score = min(95, 50 + len(friends) * 5)
    return {
        "score": score,
        "friend": friends,
        "enemy": data["enemy"],
        "neutral": data["neutral"],
    }


def build_chart(
    full_name: str,
    dob: date,
    gender: str,
    mobile_number: Optional[str] = None,
) -> Dict:
    first, last, full = split_name(full_name)
    moolank = moolank_from_dob(dob)
    bhagyank = bhagyank_from_dob(dob)
    first_compound, first_num = name_number(first) if first else (0, 0)
    last_compound, last_num = name_number(last) if last else (0, 0)
    full_compound, full_num = name_number(full) if full else (0, 0)
    zodiac, zodiac_planet = zodiac_for_dob(dob)
    loshu = build_loshu_grid(dob)
    dasha = dasha_numbers(dob)
    compat = compatibility_score(moolank)
    mobile = mobile_number_total(mobile_number) if mobile_number else None

    moolank_planet = NUMBER_PLANET.get(moolank, ("", ""))
    bhagyank_planet = NUMBER_PLANET.get(bhagyank, ("", ""))

    return {
        "full_name": full_name.strip(),
        "first_name": first,
        "last_name": last,
        "date_of_birth": dob.isoformat(),
        "dob_display": dob.strftime("%d/%m/%Y"),
        "gender": gender.upper(),
        "moolank": moolank,
        "bhagyank": bhagyank,
        "compound_day": compound_day(dob),
        "moolank_planet": moolank_planet[0],
        "bhagyank_planet": bhagyank_planet[0],
        "zodiac_sign": zodiac,
        "zodiac_planet": zodiac_planet,
        "first_name_number": first_num,
        "first_name_compound": first_compound,
        "last_name_number": last_num,
        "last_name_compound": last_compound,
        "full_name_number": full_num,
        "full_name_compound": full_compound,
        "loshu": loshu,
        "dasha": dasha,
        "compatibility": compat,
        "mobile": {
            "number": mobile_number,
            "total": mobile[0] if mobile else None,
            "reduced": mobile[1] if mobile else None,
        }
        if mobile_number
        else None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
