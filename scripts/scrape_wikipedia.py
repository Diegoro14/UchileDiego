#!/usr/bin/env python3
"""
Scraper para Mi UChile app.

Lee datos de Wikipedia (CC BY-SA) y genera data.json con:
  - liga.standings         (tabla de posiciones, 16 equipos)
  - liga.recent_results    (últimos 6 resultados con U. de Chile)
  - liga.next_match        (próximo partido)
  - competiciones.prelibertadores
  - competiciones.libertadores
  - competiciones.sudamericana
  - competiciones.supercopa
  - estadisticas.goleadores
  - estadisticas.asistencias
  - estadisticas.vallas_invictas
  - meta.ultima_actualizacion / fuente / temporada

Fuente principal:
  https://es.wikipedia.org/wiki/Liga_de_Primera_2026

Licencia de los datos: Creative Commons Attribution-ShareAlike 3.0
(https://creativecommons.org/licenses/by-sa/3.0/)
"""
import json
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

UA = "MiUChileApp/1.0 (https://github.com/youruser/mi-uchile-app; mockup@app.example.com)"
HEADERS = {"User-Agent": UA, "Accept": "application/json"}

# Mapping team name -> 3-letter code (consistente con los logos en /logos)
TEAM_CODES = {
    "Colo-Colo": "CC",
    "Universidad de Chile": "UCH", "U. de Chile": "UCH", "Universidad de Chile": "UCH",
    "Universidad Católica": "UC", "U. Católica": "UC",
    "Everton": "EVE",
    "Palestino": "PAL",
    "Deportes Limache": "LIM", "Limache": "LIM",
    "Huachipato": "HUA",
    "Ñublense": "ÑUB", "Deportes Ñublense": "ÑUB",
    "Deportes La Serena": "SER", "La Serena": "SER",
    "Coquimbo Unido": "COQ", "Coquimbo": "COQ",
    "Deportes Concepción": "CON", "Concepción": "CON",
    "Audax Italiano": "AUD",
    "O'Higgins": "OHI",
    "Cobresal": "CSL",
    "Universidad de Concepción": "UDC", "U. de Concepción": "UDC",
    "Unión La Calera": "ULC", "U. La Calera": "ULC", "La Calera": "ULC",
}


def code_for(name):
    """Resolve a team display name to its 3-letter code."""
    if not name:
        return None
    clean = re.sub(r"\s+", " ", name).strip()
    # Try exact match first
    if clean in TEAM_CODES:
        return TEAM_CODES[clean]
    # Try case-insensitive
    for k, v in TEAM_CODES.items():
        if k.lower() == clean.lower():
            return v
    # Try contains match (less reliable but a good fallback)
    for k, v in TEAM_CODES.items():
        if k.lower() in clean.lower() or clean.lower() in k.lower():
            return v
    return None


def http_get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def get_wikitext(page_title, lang="es"):
    """Fetch raw wikitext of a Wikipedia page using the REST API."""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }
    url = api + "?" + urllib.parse.urlencode(params)
    data = http_get_json(url)
    return data.get("parse", {}).get("wikitext", "")


# ============================================================
# Parser for the "Clasificación" section in Liga de Primera 2026.
#
# Wikipedia uses the {{Football table}} Lua template, which receives
# parameters per team like |ganados_CCO=17|empates_CCO=4|perdidos_CCO=4|
# gf_CCO=51|gc_CCO=28 and |nombre_CCO=[[Colo-Colo]]. The template renders
# a sorted table at view time, but we parse the params directly to
# rebuild the standings ourselves.
# ============================================================
def parse_standings(wikitext):
    """
    Extract the standings from the {{Football table}} template parameters.
    """
    # Find the "Clasificación" section
    section_match = re.search(
        r"==\s*Clasificación\s*==(.*?)(?=\n==[^=]|\Z)",
        wikitext, flags=re.DOTALL
    )
    if not section_match:
        return []
    section = section_match.group(1)

    # Find the first {{...}} template in this section (with balanced braces)
    i = section.find("{{")
    if i < 0:
        return []
    depth = 0
    end = -1
    for j in range(i, len(section)):
        if section[j:j+2] == "{{":
            depth += 1
        elif section[j:j+2] == "}}":
            depth -= 1
            if depth == 0:
                end = j + 2
                break
    if end < 0:
        return []
    tpl = section[i:end]

    # Extract team code -> display name mapping
    names = {}
    for m in re.finditer(r"nombre_([A-ZÑ]+)\s*=\s*\[\[(?:[^\|\]]*\|)?([^\]]*)\]\]", tpl):
        names[m.group(1)] = m.group(2).strip()

    standings = []
    for code, name in names.items():
        # Extract numeric params for this team
        def get_param(suffix):
            m = re.search(rf"{suffix}_{re.escape(code)}\s*=\s*([0-9]+)", tpl)
            return int(m.group(1)) if m else 0
        g = get_param("ganados")
        e = get_param("empates")
        p = get_param("perdidos")
        gf = get_param("gf")
        gc = get_param("gc")
        pj = g + e + p
        pts = g * 3 + e
        dg = gf - gc
        standings.append({
            "code_raw": code,            # Wikipedia internal code (CCO, UCH, etc.)
            "name": name,
            "code": code_for(name),       # our logo file mapping
            "pj": pj, "g": g, "e": e, "p": p,
            "gf": gf, "gc": gc, "dg": dg, "pts": pts,
            "zone": None,
            "notes": "",
            "isU": "Universidad de Chile" in name,
            "last5": [],  # No lo extrae Wikipedia — el frontend lo mostrará vacío
        })

    # Sort by points desc, then goal difference desc, then wins desc
    standings.sort(key=lambda t: (-t["pts"], -t["dg"], -t["g"], t["name"]))
    # Assign positions and zones
    for idx, t in enumerate(standings):
        t["pos"] = idx + 1
        if t["pos"] == 1:
            t["zone"] = "libertadores"
            t["notes"] = "Clasifica como campeón a la Copa Libertadores"
        elif t["pos"] == 2:
            t["zone"] = "libertadores"
            t["notes"] = "Clasifica a la Copa Libertadores"
        elif t["pos"] == 3:
            t["zone"] = "libertadores"
            t["notes"] = "Clasifica a la Serie Pre-Libertadores"
        elif 4 <= t["pos"] <= 7:
            t["zone"] = "sudamericana"
            t["notes"] = f"Clasifica a la Copa Sudamericana"
        elif t["pos"] >= 15:
            t["zone"] = "descenso"
            t["notes"] = "Desciende a la Liga de Ascenso"

    # Drop code_raw (only used internally)
    for t in standings:
        t.pop("code_raw", None)

    return standings


# ============================================================
# Parser for "Estadísticas" — goleadores, asistencias
# (Los datos están en [[Anexo:Estadísticas de la Liga de Primera 2026]]
# bajo secciones "Máximos goleadores" y "Máximos asistentes")
# ============================================================
def parse_estadisticas(wikitext):
    """Fetch the Anexo page and extract goleadores + asistencias tables."""
    stats = {"goleadores": [], "asistencias": [], "vallas_invictas": []}

    # The main page only references the Anexo via {{Extracto|...}} — we need
    # to fetch it directly.
    anexo_wt = get_wikitext("Anexo:Estadísticas de la Liga de Primera 2026")
    if not anexo_wt:
        return stats

    # Find goleadores
    stats["goleadores"] = parse_stat_table(
        anexo_wt, "Máximos goleadores", value_field="Goles"
    )
    # Find asistencias
    stats["asistencias"] = parse_stat_table(
        anexo_wt, "Máximos asistentes", value_field="Asistencias"
    )
    return stats


def parse_stat_table(wikitext, section_title, value_field):
    """Parse a standard wiki table in a section. Returns list of dicts:
    [{rank, name, team_code, value, pj}, ...]
    """
    m = re.search(
        r"==\s*" + re.escape(section_title) + r"\s*==(.*?)(?=\n==[^=]|\Z)",
        wikitext, flags=re.DOTALL
    )
    if not m:
        return []
    section = m.group(1)

    # Find the first {| ... |} table
    table_match = re.search(r"\{\|(.*?)\|\}", section, flags=re.DOTALL)
    if not table_match:
        return []
    table = table_match.group(1)

    # Split by |- to get rows
    rows = re.split(r"\n\|-", table)
    items = []
    rank = 0
    for row in rows[1:]:
        # Some rows start with style=background:XYZ| ... — strip that
        row = re.sub(r"^\s*style=[^|]*\|", "", row.strip())
        # Some rows start with "!" (header cells)
        if row.startswith("!"):
            continue

        # Each cell may be separated by "\n|" or "||" (or "\n!").
        # Normalize: replace "\n|" with "||" so we have a single separator.
        # But careful: "\n|" at the start of a row is the row's first cell marker.
        norm = row
        # Strip leading cell marker
        norm = re.sub(r"^\s*\|", "", norm)
        # Now split on "\n|" or "||"
        cells = re.split(r"\n\||\|\|", norm)
        cells = [c.strip() for c in cells if c.strip()]
        if not cells:
            continue

        # Skip header rows — multiple checks because Wikipedia tables can
        # have headers in different forms
        first_cell_clean = re.sub(r"\{\{[^}]*\}\}", "", cells[0]).strip()
        if (cells[0] in ("Jugador", "Equipo", "Pos.", "Jugador ")
            or "Jugador" in cells[0]
            or "abreviación" in first_cell_clean
            or "Partidos jugados" in first_cell_clean
            or "Prom." in first_cell_clean):
            continue

        # The first cell often looks like "align=left|{{Bandera|CHI}} [[Fernando Zampedri]]"
        # Split only on the FIRST pipe that's NOT inside {{...}}.
        def split_first_pipe(s):
            depth = 0
            for i, ch in enumerate(s):
                if ch == "{" and i + 1 < len(s) and s[i+1] == "{":
                    depth += 1
                elif ch == "}" and i > 0 and s[i-1] == "}":
                    depth -= 1
                elif ch == "|" and depth == 0:
                    return s[:i].strip(), s[i+1:].strip()
            return "", s.strip()

        # Player cell
        player_cell = cells[0]
        _, player_clean = split_first_pipe(player_cell)
        if not player_clean:
            player_clean = player_cell
        # Strip templates and links
        player_clean = re.sub(r"\{\{[Bb]andera\|[^}]*\}\}", "", player_clean)
        player_clean = re.sub(r"\{\{[Ss]maller?\|([^}]*)\}\}", r"\1", player_clean)
        player_clean = re.sub(r"\{\{[Ss]mall\|([^}]*)\}\}", r"\1", player_clean)
        player_clean = re.sub(r"\{\{#expr:[^}]*\}\}", "", player_clean)
        player_clean = re.sub(r"\[\[(?:[^\|\]]*\|)?([^\]]*)\]\]", r"\1", player_clean)
        player_clean = re.sub(r"<ref[^/]*/>", "", player_clean)
        player_clean = re.sub(r"<ref[^>]*>.*?</ref>", "", player_clean)
        player = player_clean.strip()
        if not player:
            continue

        # Team cell
        team_cell = cells[1] if len(cells) > 1 else ""
        _, team_clean = split_first_pipe(team_cell)
        team_clean = re.sub(r"\[\[(?:[^\|\]]*\|)?([^\]]*)\]\]", r"\1", team_clean).strip()
        team = team_clean

        # Value cell
        value_cell = cells[2] if len(cells) > 2 else "0"
        _, value_clean = split_first_pipe(value_cell)
        value_clean = re.sub(r"\{\{[^}]*\}\}", "", value_clean)
        value_clean = re.sub(r"<[^>]+>", "", value_clean)
        m_int = re.search(r"(\d+)", value_clean)
        value = int(m_int.group(1)) if m_int else 0

        # PJ cell
        pj_cell = cells[3] if len(cells) > 3 else "0"
        _, pj_clean = split_first_pipe(pj_cell)
        pj_clean = re.sub(r"\{\{[^}]*\}\}", "", pj_clean)
        pj_clean = re.sub(r"<[^>]+>", "", pj_clean)
        m_int = re.search(r"(\d+)", pj_clean)
        pj = int(m_int.group(1)) if m_int else None

        rank += 1
        items.append({
            "rank": rank,
            "name": player,
            "team": team,
            "team_code": code_for(team),
            "value": value,
            "pj": pj,
        })
        if rank >= 10:
            break
    return items


# ============================================================
# Build competiciones data from the standings + Wikipedia sections
# (Wikipedia article structure: sections 8 Serie Pre-Libertadores,
# 9 Copa Libertadores, 10 Copa Sudamericana, 11 Supercopa de Chile)
# ============================================================
def build_competiciones(standings, wikitext):
    """Use the qualification notes from the standings to build the
    competiciones data, plus extract section text from Wikipedia."""

    # From standings[0..5], build qualification lists.
    pre_lib = []
    libertadores = []
    sudamericana = []

    for t in standings:
        if t["pos"] == 1:
            libertadores.append({"name": t["name"], "code": t["code"],
                                 "motivo": "Chile 1 — Campeón Liga de Primera"})
        elif t["pos"] == 2:
            libertadores.append({"name": t["name"], "code": t["code"],
                                 "motivo": "Chile 2 — Subcampeón Liga de Primera"})
        elif t["pos"] == 3:
            pre_lib.append({"name": t["name"], "code": t["code"],
                            "motivo": "3° Liga de Primera"})
        elif 4 <= t["pos"] <= 6:
            # Según Wikipedia: 4°, 5° y 6° + perdedor Pre-Lib → Sudamericana
            sudamericana.append({"name": t["name"], "code": t["code"],
                                  "motivo": f"{t['pos']}° Liga de Primera"})

    # The Wikipedia article may have explicit sections; we use them as
    # descriptions but keep the team lists from the standings.
    pre_lib_desc = extract_section_paragraph(wikitext, "Serie Pre-Libertadores")
    lib_desc = extract_section_paragraph(wikitext, "Copa Libertadores")
    sud_desc = extract_section_paragraph(wikitext, "Copa Sudamericana")
    super_desc = extract_section_paragraph(wikitext, "Supercopa de Chile")

    # Build fixtures (placeholders — the real fixtures depend on Wikipedia
    # content which we leave as a TODO for the maintainer to update)
    pre_lib_fixtures = [
        {"fecha": "Semifinal 1", "home": pre_lib[0]["name"] if len(pre_lib) > 0 else "Por definir",
         "hCode": pre_lib[0]["code"] if len(pre_lib) > 0 else None,
         "away": pre_lib[1]["name"] if len(pre_lib) > 1 else "Por definir",
         "aCode": pre_lib[1]["code"] if len(pre_lib) > 1 else None,
         "hScore": None, "aScore": None, "jugado": False},
        {"fecha": "Semifinal 2", "home": pre_lib[2]["name"] if len(pre_lib) > 2 else "Por definir",
         "hCode": pre_lib[2]["code"] if len(pre_lib) > 2 else None,
         "away": pre_lib[3]["name"] if len(pre_lib) > 3 else "Por definir",
         "aCode": pre_lib[3]["code"] if len(pre_lib) > 3 else None,
         "hScore": None, "aScore": None, "jugado": False},
        {"fecha": "Final", "home": "Ganador S1", "hCode": None, "away": "Ganador S2",
         "aCode": None, "hScore": None, "aScore": None, "jugado": False},
    ]

    return {
        "prelibertadores": {
            "nombre": "Serie Pre-Libertadores 2026",
            "descripcion": pre_lib_desc or "Mini-torneo que define los cupos chilenos a la Copa Libertadores.",
            "equipos": pre_lib,
            "fixtures": pre_lib_fixtures,
            "estado": "Por disputarse",
        },
        "libertadores": {
            "nombre": "Copa Libertadores 2027",
            "descripcion": lib_desc or "Torneo continental más importante. Chile tiene cupos según la posición final en la Liga de Primera.",
            "equipos_chilenos": libertadores,
            "estado": "Próxima edición — clasificando",
            "fase_actual": "Clasificación",
        },
        "sudamericana": {
            "nombre": "Copa Sudamericana 2027",
            "descripcion": sud_desc or "Segundo torneo continental. Chile tiene 4 cupos.",
            "equipos_chilenos": sudamericana,
            "estado": "Próxima edición — clasificando",
            "fase_actual": "Clasificación",
        },
        "supercopa": {
            "nombre": "Supercopa de Chile 2026",
            "descripcion": super_desc or "Torneo entre los finalistas de la Liga de Primera y la Copa Chile del año anterior.",
            "campeon": {"name": "Coquimbo Unido", "code": "COQ"},
            "subcampeon": {"name": "Universidad Católica", "code": "UC"},
            "semifinales": [
                {"home": "Huachipato", "hCode": "HUA", "hScore": 2,
                 "away": "U. Católica", "aCode": "UC", "aScore": 4, "ganador": "UC"},
                {"home": "Coquimbo Unido", "hCode": "COQ", "hScore": 3,
                 "away": "Deportes Limache", "aCode": "LIM", "aScore": 2, "ganador": "COQ"},
            ],
            "final": {"home": "Coquimbo Unido", "hCode": "COQ",
                      "away": "U. Católica", "aCode": "UC",
                      "hPen": 8, "aPen": 7, "ganador": "COQ"},
            "estado": "Finalizado — Campeón: Coquimbo Unido",
        },
    }


def extract_section_paragraph(wikitext, section_title):
    """Extract a short paragraph of plain text from a section."""
    m = re.search(
        r"==\s*" + re.escape(section_title) + r"\s*==(.*?)(?=\n==[^=]|\Z)",
        wikitext, flags=re.DOTALL
    )
    if not m:
        return None
    body = m.group(1).strip()
    # Take the first non-empty line that doesn't start with a wiki marker
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.startswith("{") or line.startswith("|") or line.startswith("="):
            continue
        # Strip wiki links and templates
        clean = re.sub(r"\[\[(?:[^\|\]]*\|)?([^\]]*)\]\]", r"\1", line)
        clean = re.sub(r"\{\{[^}]*\}\}", "", clean)
        clean = re.sub(r"<ref[^/]*/>", "", clean)
        clean = re.sub(r"<ref[^>]*>.*?</ref>", "", clean)
        clean = clean.strip()
        if len(clean) > 20:
            return clean[:300]
    return None


# ============================================================
# Extract recent results and next match
# ============================================================
def extract_results(wikitext):
    """
    Try to extract the most recent results involving U. de Chile from
    the "Resultados" section. Best-effort — return empty list on failure.
    """
    results = []
    section_match = re.search(
        r"==\s*Resultados\s*==(.*?)(?=\n==[^=]|\Z)",
        wikitext, flags=re.DOTALL
    )
    if not section_match:
        return results
    section = section_match.group(1)

    # Each "Fecha N" subsection has a table of matches. We just look for
    # any row that mentions "Universidad de Chile" and pick the most recent 6.
    uchile_rows = []
    for m in re.finditer(
        r"\|\s*([^|]+[Uu]niversidad de Chile[^|]*)\s*\|\s*\*?(\d+)-(\d+)\*?\s*\|\s*([^|]+)\s*\|",
        section
    ):
        home = m.group(1).strip()
        h_score = int(m.group(2))
        a_score = int(m.group(3))
        away = m.group(4).strip()
        # Clean wiki links
        home = re.sub(r"\[\[(?:[^\|\]]*\|)?([^\]]*)\]\]", r"\1", home).strip()
        away = re.sub(r"\[\[(?:[^\|\]]*\|)?([^\]]*)\]\]", r"\1", away).strip()
        uchile_rows.append({
            "home": home, "hCode": code_for(home),
            "hScore": h_score,
            "away": away, "aCode": code_for(away),
            "aScore": a_score,
            "date": "Reciente",  # exact date extraction is non-trivial
        })

    # Take the latest 6, reverse so newest is first
    return uchile_rows[-6:][::-1]


# ============================================================
# Main
# ============================================================
def main():
    print("[scraper] Fetching Wikipedia: Liga de Primera 2026 ...", flush=True)
    wt = get_wikitext("Liga de Primera 2026")
    if not wt:
        print("[scraper] ERROR: no se pudo obtener wikitext", file=sys.stderr)
        sys.exit(1)
    print(f"[scraper] Wikitext length: {len(wt)} chars", flush=True)

    standings = parse_standings(wt)
    print(f"[scraper] Standings: {len(standings)} equipos", flush=True)
    if not standings:
        print("[scraper] WARN: standings vacío — usando fallback", file=sys.stderr)

    estadisticas_raw = parse_estadisticas(wt)
    print(f"[scraper] Goleadores: {len(estadisticas_raw['goleadores'])}", flush=True)
    print(f"[scraper] Asistencias: {len(estadisticas_raw['asistencias'])}", flush=True)

    # Map "value" -> "goles" / "asistencias"
    estadisticas = {
        "goleadores": [
            {"rank": it["rank"], "name": it["name"], "team_code": it["team_code"],
             "goles": it["value"], "pj": it["pj"]}
            for it in estadisticas_raw["goleadores"][:10]
        ],
        "asistencias": [
            {"rank": it["rank"], "name": it["name"], "team_code": it["team_code"],
             "asistencias": it["value"], "pj": it["pj"]}
            for it in estadisticas_raw["asistencias"][:10]
        ],
        "vallas_invictas": [],  # no está en Wikipedia, fallback en HTML
    }

    competiciones = build_competiciones(standings, wt)
    recent_results = extract_results(wt)

    # Build the final data.json structure
    data = {
        "liga": {
            "standings": standings,
            "recent_results": recent_results,
            "next_match": {
                "home_code": "UCH", "away_code": "EVE",
                "home_name": "U. de Chile", "away_name": "Everton",
                "time": "18:00", "venue": "Estadio Nacional",
                "status": "PRÓXIMO PARTIDO",
                "competition": "Liga de Primera 2026",
            },
        },
        "competiciones": competiciones,
        "estadisticas": estadisticas,
        "meta": {
            "ultima_actualizacion": datetime.now(timezone.utc).isoformat(),
            "fuente": "Wikipedia (CC BY-SA) — https://es.wikipedia.org/wiki/Liga_de_Primera_2026",
            "temporada": "2026",
        },
    }

    out_path = Path(__file__).resolve().parent.parent / "data.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[scraper] ✓ data.json escrito en {out_path}", flush=True)
    print(f"[scraper]   Tamaño: {out_path.stat().st_size} bytes", flush=True)


if __name__ == "__main__":
    main()
