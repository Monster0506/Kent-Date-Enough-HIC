"""Kent State Banner CRN scraper.

Two-step lookup per CRN:
  1. Detail page  -> course name, subject, course number
  2. List search  -> days, time, building, instructor
"""

import re
import urllib.error
import urllib.parse
import urllib.request

TERM = "202610" 
_UA = "Mozilla/5.0 (compatible; KentDateEnough/1.0)"


def _fetch(url: str, *, data: bytes | None = None) -> str:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _get_subj_course(crn: str) -> tuple[str, str, str] | tuple[None, None, None]:
    url = (
        f"https://keys.kent.edu/ePROD/bwckschd.p_disp_detail_sched"
        f"?term_in={TERM}&crn_in={crn}"
    )
    try:
        html = _fetch(url)
    except (urllib.error.URLError, OSError):
        return None, None, None

    m = re.search(
        r'ddlabel[^>]*>\s*(.+?)\s*-\s*' + re.escape(crn) + r'\s*-\s*([A-Z]+)\s+(\d+)\s*-\s*\d+',
        html,
        re.DOTALL,
    )
    if not m:
        return None, None, None
    return _clean(m.group(1)), m.group(2).strip(), m.group(3).strip()


def _get_section_row(subj: str, course_num: str, target_crn: str) -> list[str] | None:
    """Returns the list of cleaned <td> values for the section row."""
    params = urllib.parse.urlencode([
        ("term_in", TERM),
        ("sel_subj", "dummy"), ("sel_day", "dummy"), ("sel_schd", "dummy"),
        ("sel_insm", "dummy"), ("sel_loc", "dummy"), ("sel_levl", "dummy"),
        ("sel_sess", "dummy"), ("sel_instr", "dummy"), ("sel_ptrm", "dummy"),
        ("sel_attr", "dummy"), ("sel_camp", "dummy"),
        ("sel_subj", subj), ("sel_crse", course_num), ("sel_title", ""),
        ("sel_camp", "%"), ("sel_insm", "%"), ("sel_from_cred", ""), ("sel_to_cred", ""),
        ("sel_loc", "%"), ("sel_levl", "%"), ("sel_ptrm", "%"), ("sel_instr", "%"),
        ("sel_attr", "%"),
        ("begin_hh", "0"), ("begin_mi", "0"), ("begin_ap", "a"),
        ("end_hh",   "0"), ("end_mi",   "0"), ("end_ap",   "a"),
    ])
    url = f"https://keys.kent.edu/ePROD/bwlkffcs.P_AdvUnsecureGetCrse?{params}"
    try:
        html = _fetch(url)
    except (urllib.error.URLError, OSError):
        return None

    idx = html.find(f">{target_crn}<")
    if idx < 0:
        return None

    row_start = html.rfind("<tr", 0, idx)
    row_end   = html.find("</tr>", idx) + 5
    cells_raw = re.findall(r"<[Tt][Dd][^>]*>(.*?)</[Tt][Dd]>", html[row_start:row_end], re.DOTALL)
    return [_clean(c) for c in cells_raw]


def lookup_crn(crn: str) -> dict | None:
    crn = crn.strip()
    if not crn.isdigit():
        return None

    name, subj, course_num = _get_subj_course(crn)
    if not subj:
        return None

    row = _get_section_row(subj, course_num, crn)
    if not row or len(row) < 15:
        return None

    method   = row[14] if len(row) > 14 else ""
    in_person = method == "In-Person"
    location  = row[15] if in_person else method
    instr_raw = row[16] if (in_person and len(row) > 16) else (row[15] if len(row) > 15 else "")
    instructor = re.sub(r"\s*\(\s*P\s*\)\s*", "", instr_raw).strip()

    return {
        "crn":        crn,
        "subject":    subj,
        "course_num": course_num,
        "name":       name,
        "days":       row[12] if len(row) > 12 else "TBA",
        "time":       row[13] if len(row) > 13 else "TBA",
        "location":   location,
        "instructor": instructor,
        "term":       TERM,
    }


def lookup_crns(crns: list[str]) -> list[dict]:
    results = []
    for crn in crns:
        info = lookup_crn(crn)
        if info:
            results.append(info)
    return results
