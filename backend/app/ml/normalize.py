"""
normalize.py — cleaning & attribute extraction (Stage 1 of the pipeline).

Turns a raw, messy material row into:
  * a canonical UPPERCASE `clean_desc` (abbreviations expanded, separators/UOM
    standardized, vendor noise stripped),
  * a standardized UOM,
  * a detected `category` (used for blocking), and
  * a dict of structured `attributes` parsed from the free text.

Attribute extraction is CATEGORY-AWARE: after a coarse category is detected
from common specs + keywords, a controlled vocabulary per category pulls out
the *type discriminators* that define identity (a CENTRIFUGAL pump is not a
SUBMERSIBLE pump; a GATE valve is not a GLOBE valve; an ARMOURED cable is not
an UNARMOURED one). Type words are matched fuzzily so typos ("SUBMERISBLE",
"SHPERICAL") still resolve. These structured attributes are what let the
matcher say "M10 != M12" and "BALL != ROLLER" instead of over-merging on text.

Reference dictionaries live in `data/reference/`. No third-party deps.
"""
import difflib
import json
import re
from pathlib import Path

_REF = Path(__file__).resolve().parents[3] / "data" / "reference"
ABBR = json.loads((_REF / "abbreviations.json").read_text())
UOM_MAP = json.loads((_REF / "uom_map.json").read_text())

_VENDOR_NOISE = [
    r"\bMAKE\s+[A-Z&]+\b", r"\bAS\s+PER\b", r"\bREF\s+DWG\b",
    r"\bIS\s?\d+\b", r"\bASTM\s?[A-Z0-9]+\b",
]


def normalize_uom(uom):
    if not uom:
        return "EACH"
    key = uom.strip().upper().rstrip(".")
    return UOM_MAP.get(key, UOM_MAP.get(uom.strip().upper(), key or "EACH"))


def _basic_clean(text):
    s = (text or "").upper()
    s = re.sub(r"(?<=[0-9A-Z])[X*](?=[0-9])", " X ", s)   # 3.5CX6 -> 3.5C X 6
    s = re.sub(r"\bSQ[\s.]*MM\b", "SQMM", s)
    s = re.sub(r"\bMM2\b", "SQMM", s)
    for pat in _VENDOR_NOISE:
        s = re.sub(pat, " ", s)
    s = re.sub(r"[,_/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def expand_abbreviations(text):
    out = []
    for tok in text.split():
        for cand in (tok, tok.strip(".,"), tok.replace(".", "")):
            if cand in ABBR:
                out.append(ABBR[cand])
                break
        else:
            out.append(tok)
    return " ".join(out)


def _present(term, s, toks, cutoff=0.8):
    """True if `term` appears in the text (exact, multi-word, or fuzzy token)."""
    if term in s:
        return True
    words = term.split()
    if len(words) > 1:
        return all(w in s for w in words)
    return any(len(t) >= 4 and difflib.SequenceMatcher(None, t, term).ratio() >= cutoff
               for t in toks)


def _material(s):
    """Robust material detection: exact multi-word terms, then keyword fallback
    (survives dropped/abbreviated tokens like 'C.STEEL' or a lone 'IRON')."""
    for term in ("STAINLESS STEEL", "CARBON STEEL", "CAST IRON",
                 "GALVANIZED IRON", "MILD STEEL"):
        if term in s:
            return term
    if "STAINLESS" in s:
        return "STAINLESS STEEL"
    if "CARBON" in s:
        return "CARBON STEEL"
    if "MILD" in s:
        return "MILD STEEL"
    if "GALVANIZED" in s:
        return "GALVANIZED IRON" if "IRON" in s else "GALVANIZED"
    if "COPPER" in s:
        return "COPPER"
    if "ALUMINIUM" in s:
        return "ALUMINIUM"
    if "CAST" in s or "IRON" in s:
        return "CAST IRON"
    return None


def _extract_common(s):
    """Category-independent numeric / material specs."""
    a = {}
    m = re.search(r"\bM(\d{1,2})\b", s)
    if m:
        a["thread"] = f"M{m.group(1)}"
    m = re.search(r"(\d+(?:\.\d+)?)\s*MM\b", s)
    if m:
        a["size_mm"] = float(m.group(1))
    m = re.search(r"\bSCH(?:EDULE)?\s*0*(\d+)\b", s)
    if m:
        a["schedule"] = f"SCH{m.group(1)}"
    m = re.search(r"\b(PN\d+|CL\d+)\b", s)
    if m:
        a["rating"] = m.group(1)
    m = (re.search(r"STAINLESS STEEL\s*(\d{3})", s)
         or re.search(r"\b(304|316)\b", s))
    if m:
        a["grade"] = f"SS{m.group(1)}"
    else:
        m = (re.search(r"GRADE\s*(\d+(?:\.\d+)?)", s)
             or re.search(r"\b(4\.6|8\.8|10\.9|12\.9)\b", s))
        if m:
            a["grade"] = f"GR{m.group(1)}"
    mat = _material(s)
    if mat:
        a["material"] = mat
    m = re.search(r"\b(\d+(?:\.\d+)?)C\b", s)         # cable cores: 3C / 3.5C
    if m:
        a["cores"] = f"{m.group(1)}C"
    m = re.search(r"(\d+(?:\.\d+)?)\s*SQMM", s)
    if m:
        a["csa"] = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*KV", s)
    if m:
        a["voltage"] = float(m.group(1))
    if "XLPE" in s:
        a["insulation"] = "XLPE"
    elif re.search(r"\bPVC\b", s):
        a["insulation"] = "PVC"
    m = re.search(r"(\d+(?:\.\d+)?)\s*HP", s)
    if m:
        a["hp"] = float(m.group(1))
    m = re.search(r"\b(ZZ|2RS)\b", s)
    if m:
        a["seal"] = m.group(1)
    return a


def detect_category(s, hintraw, attrs):
    hint = (hintraw or "").upper()
    if "seal" in attrs:
        return "BEARING"
    if "BEARING" in s or any(k in hint for k in ("BEARING", "BRG")):
        return "BEARING"
    if re.search(r"\b\d{4,5}\b", s) and any(w in s for w in ("BALL", "ROLLER", "TAPER", "SPHERICAL")):
        return "BEARING"
    if "csa" in attrs or "voltage" in attrs or "cores" in attrs or "CABLE" in s:
        return "CABLE"
    if "hp" in attrs or "PUMP" in s:
        return "PUMP"
    if "schedule" in attrs or any(w in s for w in ("PIPE", "SEAMLESS", "ERW")):
        return "PIPE"
    if "VALVE" in s:
        return "VALVE"
    if any(w in s for w in ("GASKET", "SPIRAL WOUND", "GRAPHITE", "CAF", "RING JOINT", "PTFE")):
        return "GASKET"
    if "thread" in attrs or any(w in s for w in ("BOLT", "NUT", "WASHER", "STUD", "ALLEN")):
        return "FASTENER"
    for cat, kws in (("BEARING", ("BRG",)), ("VALVE", ("VLV",)), ("GASKET", ("GSKT", "GKT"))):
        if any(k in hint for k in kws):
            return cat
    return "OTHER"


def _extract_types(s, cat, toks):
    """Category-specific controlled-vocabulary discriminators."""
    a = {}
    if cat == "BEARING":
        if _present("TAPER", s, toks):
            a["btype"] = "TAPER ROLLER"
        elif _present("SPHERICAL", s, toks):
            a["btype"] = "SPHERICAL ROLLER"
        elif _present("ROLLER", s, toks):
            a["btype"] = "ROLLER"
        elif _present("BALL", s, toks):
            a["btype"] = "BALL"
        m = re.search(r"\bNU\d{3}\b", s) or re.search(r"\b(\d{4,5})\b", s)
        if m:
            a["code_no"] = m.group(0)
    elif cat == "VALVE":
        for v in ("GATE", "GLOBE", "BUTTERFLY", "CHECK", "BALL"):
            if _present(v, s, toks):
                a["vtype"] = v
                break
        for e in ("FLANGED", "SCREWED", "WAFER"):
            if _present(e, s, toks):
                a["ends"] = e
                break
    elif cat == "PUMP":
        for p in ("CENTRIFUGAL", "SUBMERSIBLE", "GEAR", "SCREW"):
            if _present(p, s, toks):
                a["ptype"] = p
                break
    elif cat == "PIPE":
        for p in ("SEAMLESS", "ERW", "WELDED"):
            if _present(p, s, toks):
                a["ptype"] = p
                break
    elif cat == "CABLE":
        if "UNARM" in s:
            a["armour"] = "UNARMOURED"
        elif "ARMOURED" in s or re.search(r"\bARM\b", s):
            a["armour"] = "ARMOURED"
    elif cat == "GASKET":
        for kw, label in (("SPIRAL", "SPIRAL WOUND"), ("RING", "RING JOINT"),
                          ("PTFE", "PTFE"), ("CAF", "CAF")):
            if _present(kw, s, toks):
                a["gtype"] = label
                break
    elif cat == "FASTENER":
        if _present("WASHER", s, toks):
            a["sub"] = ("SPRING WASHER" if _present("SPRING", s, toks)
                        else "PLAIN WASHER" if _present("PLAIN", s, toks) else "WASHER")
        elif _present("NUT", s, toks):
            a["sub"] = "NUT"
        elif _present("STUD", s, toks):
            a["sub"] = "STUD BOLT"
        elif _present("ALLEN", s, toks):
            a["sub"] = "ALLEN BOLT"
        elif _present("BOLT", s, toks):
            a["sub"] = "HEX BOLT"
        for fin in ("GALVANIZED", "ZINC", "PLAIN", "BLACK"):
            if _present(fin, s, toks):
                a["finish"] = fin
                break
    return a


def normalize_record(description, uom="", category_raw=""):
    clean = _basic_clean(expand_abbreviations(_basic_clean(description)))
    toks = clean.split()
    attrs = _extract_common(clean)
    category = detect_category(clean, category_raw, attrs)
    attrs.update(_extract_types(clean, category, toks))
    return {
        "clean_desc": clean,
        "uom_std": normalize_uom(uom),
        "category": category,
        "attributes": attrs,
        "tokens": toks,
    }
