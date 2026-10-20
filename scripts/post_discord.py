import json, os, time, urllib.request
from datetime import datetime

BASE = "https://ilycons.github.io/metalstorm/"
HEADERS = {"User-Agent": "metalstorm-discord-bot/1.0"}
SLOT_S = 1800

MODES = {
    "tdm":  ("Combate a muerte por equipos", "Team Deathmatch", 0x4A9BE0),
    "as":   ("Superioridad aérea", "Air Superiority", 0x2FBCD6),
    "pt":   ("Objetivo prioritario", "Priority Target", 0xA06AD9),
    "ctf":  ("Captura la bandera", "Capture the Flag", 0xE0B41F),
    "vip":  ("Combate a muerte vip", "VIP Deathmatch", 0x37CC8F),
    "elim": ("Eliminación", "Elimination", 0x9AA5B5),
}
MODO_IDS = {
    "deathmatch": "tdm", "control": "as", "prioritytarget": "pt",
    "capturetheflag": "ctf", "elimination": "elim", "vipdeathmatch": "vip",
}
MAPAS = {
    "Arctic": {"base": "Rumbo al hielo", "night": "Noche rumbo al hielo", "snow": "Nieve rumbo al hielo"},
    "Canyon": {"base": "Cañón carmesí", "night": "Noche de cañón carmesí", "sunrise": "Sonrisa cañón carmesí"},
    "Seastacks": {"base": "Tormenta desatada", "night": "Noche de tormenta desatada"},
    "Stoneforest": {"base": "Bosque de Piedra", "night": "Noche del Bosque de Piedra"},
    "Volcano": {"base": "Crisol", "night": "Noche de crisol"},
    "Countdown": {"base": "Cuenta atrás", "night": "Noche de cuenta atrás"},
    "Enclave": {"base": "Enclave"},
}


def get_json(nombre):
    req = urllib.request.Request(f"{BASE}{nombre}?t={int(time.time())}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def nombre_mapa(mapa, variante):
    m = MAPAS.get(mapa)
    if m:
        return m.get(variante) or m["base"]
    return mapa + (f" ({variante})" if variante and variante != "day" else "")


def slot_de(rot, ts):
    n = len(rot["slots"])
    i = ((ts - rot["referenceUnixSeconds"]) // rot["slotSeconds"]) % n
    partes = str(rot["slots"][i]).split(":")
    mapa = partes[0]
    variante = partes[1] if len(partes) > 1 and partes[1] else "day"
    modo = partes[2] if len(partes) > 2 and partes[2] else "deathmatch"
    return MODO_IDS.get(modo, modo), nombre_mapa(mapa, variante)


def parse_fecha(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def cargar_reglas():
    reglas = []
    try:
        for r in get_json("eventos.json").get("reglas", []):
            try:
                ini, fin = parse_fecha(r["desde"]), parse_fecha(r["hasta"])
            except Exception:
                continue
            if fin <= ini or not r.get("modo"):
                continue
            nuevo = r.get("modoNuevo")
            if nuevo and r["modo"] not in MODES:
                MODES[r["modo"]] = (
                    nuevo.get("es", r["modo"]), nuevo.get("en", r["modo"]), 0x8FA3B3)
            reglas.append((ini, fin, r["modo"], r.get("titulo", "")))
    except Exception:
        pass
    return reglas


def info_modo(modo_id):
    return MODES.get(modo_id, (modo_id, modo_id, 0x8FA3B3))


def estado(rot, reglas, ts):
    modo_id, mapa = slot_de(rot, ts)
    evento = ""
    for ini, fin, modo, titulo in reglas:
        if ini <= ts < fin:
            modo_id, evento = modo, titulo
            break
    es, en, color = info_modo(modo_id)
    return es, en, color, mapa, evento


def main():
    rot = get_json("rotacion.json")
    reglas = cargar_reglas()
    ahora = int(time.time())
    inicio = ahora - (ahora % SLOT_S)
    fin = inicio + SLOT_S

    es, en, color, mapa, evento = estado(rot, reglas, ahora)
    nes, nen, _, nmapa, _ = estado(rot, reglas, fin)

    desc = f"**Mapa:** {mapa}\n"
    if evento:
        desc += f"**Evento:** {evento}\n"
    desc += f"**Cambia:** <t:{fin}:R> (<t:{fin}:t>)\n\n"
    desc += f"**Siguiente:** {nes} ({nen}) — {nmapa}"

    payload = {"embeds": [{
        "title": f"Ahora: {es}",
        "url": BASE,
        "description": desc,
        "color": color,
        "footer": {"text": f"{en} · Rotación de Metalstorm"},
    }]}

    req = urllib.request.Request(
        os.environ["DISCORD_WEBHOOK_URL"],
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **HEADERS},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        print("Discord respondió:", r.status)


if __name__ == "__main__":
    main()
