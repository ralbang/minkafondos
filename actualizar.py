#!/usr/bin/env python3
"""Actualiza convocatorias.json buscando en la web (API de Anthropic + web_search).
Requisitos: pip install anthropic requests ; variable de entorno ANTHROPIC_API_KEY.
Uso diario: python actualizar.py   (o con el workflow de GitHub incluido)."""
import json, re, datetime, pathlib, requests, anthropic

RUTA = pathlib.Path(__file__).with_name("convocatorias.json")
HOY = datetime.date.today().isoformat()
MODELO = "claude-sonnet-5-5"

PROMPT = f"""Hoy es {HOY}. Busca en la web convocatorias REALES, ABIERTAS o que abren en menos de 90 días,
para entidades sin ánimo de lucro en Colombia (JAC, asociaciones, fundaciones, cooperativas, resguardos,
consejos comunitarios) que financien infraestructura social, proyectos agropecuarios o comunitarios,
con montos superiores a COP 10 millones. Consulta fuentes oficiales: ADR, MinAgricultura, Prosperidad Social,
MinVivienda, MinAmbiente, MinInterior, Minciencias, APC Colombia, PNUD/PPD, UE, fundaciones y cooperación.
Responde SOLO con un arreglo JSON, sin texto adicional. Cada elemento:
{{"id":"slug","nombre":"","entidad":"","cats":["infra"|"agro"|"comun"],
"orgs":["JAC"|"asociacion"|"fundacion"|"cooperativa"|"resguardo"|"consejo"],
"min":null,"max":null,"apertura":"AAAA-MM-DD"|null,"cierre":"AAAA-MM-DD"|null,
"estado":"abierta"|"recurrente","meses":[],"url":"enlace directo a la convocatoria",
"req":["personeria","rut","estatutos","rte","cuenta","contab","rl","exp","cap","ctrl","pla","rup","aliado","cofin","mga"],
"nota":"una frase con lo clave y lo que no pudiste verificar"}}
No inventes fechas ni enlaces: si no los confirmas en la fuente, usa null y dilo en la nota."""

def enlace_vivo(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        return r.status_code < 400
    except requests.RequestException:
        return False

def buscar():
    cli = anthropic.Anthropic()
    msg = cli.messages.create(
        model=MODELO, max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 15}],
        messages=[{"role": "user", "content": PROMPT}])
    texto = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r"\[.*\]", texto, re.S)
    return json.loads(m.group(0)) if m else []

def main():
    base = json.loads(RUTA.read_text(encoding="utf-8"))
    por_url = {c["url"]: c for c in base["convocatorias"]}
    nuevas = 0
    for c in buscar():
        if not c.get("url") or not enlace_vivo(c["url"]):
            continue                                  # descarta enlaces rotos o inventados
        if c.get("cierre") and c["cierre"] < HOY:
            continue                                  # descarta ya cerradas
        c["verificado"] = HOY
        nuevas += c["url"] not in por_url
        por_url[c["url"]] = {**por_url.get(c["url"], {}), **c}
    final = []
    for c in por_url.values():
        if c.get("cierre") and c["cierre"] < HOY:
            c["estado"] = "cerrada"                   # la herramienta la oculta de las alertas
        c["enlace_ok"] = enlace_vivo(c["url"])
        final.append(c)
    RUTA.write_text(json.dumps({"actualizado": HOY, "convocatorias": final},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(final)} convocatorias, {nuevas} nuevas")

if __name__ == "__main__":
    main()
