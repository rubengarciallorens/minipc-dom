#!/usr/bin/env python3

import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path


RSS_URL = os.getenv("RSS_URL", "https://www.chollometro.com/rss")
MAX_PRICE = Decimal(os.getenv("MAX_PRICE", "100"))
STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
MAX_SEEN = 500

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

MINIPC_TERMS = (
    "mini pc",
    "mini-pc",
    "minipc",
    "micro pc",
    "micro-pc",
    "intel nuc",
    "nuc pc",
)

KNOWN_BRANDS = (
    "beelink",
    "minisforum",
    "gmktec",
    "nipogi",
    "trigkey",
    "acemagic",
    "ace magician",
    "chuwi larkbox",
    "firebat",
    "bosgame",
    "aoostar",
    "morefine",
    "mele quieter",
    "geekom",
    "kamrui",
    "blackview mp",
    "asus pn",
    "lenovo tiny",
    "dell micro",
    "hp elitedesk mini",
    "hp prodesk mini",
)

CPU_TERMS = (
    "n95",
    "n97",
    "n100",
    "n150",
    "n200",
    "n305",
    "n5095",
    "n5105",
    "n6005",
    "j4125",
    "j6412",
    "alder lake-n",
    "twin lake",
    "ryzen 3",
    "ryzen 5",
    "ryzen 7",
    "core i3",
    "core i5",
    "core i7",
)

TITLE_EXCLUSIONS = (
    "barebone",
    "barebones",
    "sin ram",
    "sin memoria",
    "sin ssd",
    "no incluye ram",
    "no incluye ssd",
    "placa base",
    "motherboard",
    "carcasa para",
    "caja para mini",
    "soporte para mini",
    "adaptador para mini",
    "fuente para mini",
    "cargador para mini",
    "tv box",
    "android box",
    "raspberry pi",
    "orange pi",
)

PRICE_PATTERNS = (
    re.compile(r"(?<![\d.,])(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:€|eur\b)", re.I),
    re.compile(r"(?:€|eur\b)\s*(\d{1,4}(?:[.,]\d{1,2})?)", re.I),
)


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MiniPCHomeAssistantMonitor/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"El RSS respondió con HTTP {response.status}")
        return response.read()


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def child_text(node, *names):
    wanted = {name.lower() for name in names}
    for child in node.iter():
        if local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""


def entry_link(node):
    for child in node.iter():
        if local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        if href:
            return href
        if child.text:
            return child.text.strip()
    return ""


def plain_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    nodes = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}]
    entries = []

    for node in nodes:
        title = plain_text(child_text(node, "title"))
        description = plain_text(child_text(node, "description", "summary", "encoded", "content"))
        link = entry_link(node)
        guid = child_text(node, "guid", "id")
        published = child_text(node, "pubdate", "published", "updated")
        structured_price = child_text(
            node,
            "dealprice",
            "currentprice",
            "offerprice",
            "price",
        )
        identity_source = guid or link or f"{title}|{published}"
        entry_id = hashlib.sha256(identity_source.encode("utf-8")).hexdigest()[:24]

        entries.append(
            {
                "id": entry_id,
                "title": title,
                "description": description,
                "link": link,
                "published": published,
                "structured_price": structured_price,
            }
        )

    return entries


def parse_decimal(value):
    cleaned = re.sub(r"[^\d.,]", "", value or "")
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")

    try:
        price = Decimal(cleaned)
    except InvalidOperation:
        return None

    return price if Decimal("0") < price < Decimal("10000") else None


def prices_in(text):
    prices = []
    for pattern in PRICE_PATTERNS:
        for match in pattern.finditer(text or ""):
            price = parse_decimal(match.group(1))
            if price is not None and price not in prices:
                prices.append(price)
    return prices


def extract_price(entry):
    structured = parse_decimal(entry.get("structured_price", ""))
    if structured is not None:
        return structured

    title_prices = prices_in(entry.get("title", ""))
    if title_prices:
        return title_prices[0]

    description_prices = prices_in(entry.get("description", ""))
    if description_prices:
        return description_prices[0]

    return None


def is_suitable_minipc(entry):
    title = entry["title"].lower()
    text = f"{entry['title']} {entry['description']}".lower()

    if any(term in title for term in TITLE_EXCLUSIONS):
        return False

    has_form_factor = any(term in text for term in MINIPC_TERMS)
    has_brand = any(term in text for term in KNOWN_BRANDS)
    has_cpu = any(term in text for term in CPU_TERMS)

    # También aceptamos títulos tipo "Beelink EQ12 N100", aunque no escriban
    # literalmente "mini PC", si coinciden marca conocida y procesador válido.
    return (has_form_factor and (has_cpu or has_brand)) or (has_brand and has_cpu)


def first_match(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return match.group(0)
    return None


def detected_specs(entry):
    text = f"{entry['title']} {entry['description']}"
    cpu = first_match(
        text,
        (
            r"Intel\s+(?:Processor\s+)?N(?:95|97|100|150|200|305)\b",
            r"\bN(?:95|97|100|150|200|305)\b",
            r"\bN(?:5095|5105|6005)\b",
            r"\bJ(?:4125|6412)\b",
            r"Ryzen\s+[357]\s+[A-Z0-9-]+",
            r"Core\s+i[357][ -][A-Z0-9-]+",
        ),
    )
    ram = first_match(text, (r"\b(?:4|8|12|16|24|32)\s*GB\s+(?:DDR\d|RAM)\b",))
    storage = first_match(
        text,
        (r"\b(?:64|128|256|512)\s*GB\s+(?:SSD|NVMe|eMMC)\b", r"\b1\s*TB\s+(?:SSD|NVMe)\b"),
    )

    parts = [part for part in (cpu, ram, storage) if part]
    return " · ".join(parts) if parts else "Revisa RAM, SSD y Ethernet en el anuncio"


def format_price(price):
    return f"{price:.2f}".replace(".", ",").rstrip("0").rstrip(",") + " €"


def telegram_send(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")

    endpoint = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": "false",
        }
    ).encode("utf-8")
    request = urllib.request.Request(endpoint, data=payload, method="POST")

    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
        if response.status != 200 or not body.get("ok"):
            raise RuntimeError(f"Telegram rechazó el mensaje: {body}")


def load_state():
    if not STATE_FILE.exists():
        return {"initialized": False, "seen": []}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {
            "initialized": bool(data.get("initialized", False)),
            "seen": list(data.get("seen", [])),
        }
    except (json.JSONDecodeError, OSError, TypeError):
        return {"initialized": False, "seen": []}


def save_state(state):
    state["seen"] = state["seen"][-MAX_SEEN:]
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def matching_deals(entries):
    matches = []
    for entry in entries:
        if not is_suitable_minipc(entry):
            continue

        price = extract_price(entry)
        if price is None:
            print(f"Sin precio fiable: {entry['title']}")
            continue

        if price >= MAX_PRICE:
            print(f"Descartado por precio ({price} €): {entry['title']}")
            continue

        entry["price"] = price
        matches.append(entry)

    return matches


def main():
    entries = parse_feed(fetch(RSS_URL))
    if not entries:
        raise RuntimeError("El RSS no contiene entradas")

    state = load_state()
    seen = set(state["seen"])
    matches = matching_deals(entries)

    if not state["initialized"]:
        state["initialized"] = True
        for entry in matches:
            if entry["id"] not in seen:
                state["seen"].append(entry["id"])
                seen.add(entry["id"])
        save_state(state)
        telegram_send(
            "Vigilancia de Chollometro activada.\n\n"
            "Te avisaré de mini-PC completos y razonables para Home Assistant "
            "cuando el precio detectado sea inferior a 100 €."
        )
        print(f"Inicializado con {len(entries)} entradas y {len(matches)} coincidencias actuales")
    else:
        new_matches = [entry for entry in matches if entry["id"] not in seen]

        for entry in reversed(new_matches):
            message = (
                "🔥 Mini-PC por menos de 100 €\n\n"
                f"{entry['title']}\n\n"
                f"💰 {format_price(entry['price'])}\n"
                f"🖥️ {detected_specs(entry)}\n\n"
                f"{entry['link']}"
            )
            telegram_send(message)
            state["seen"].append(entry["id"])
            seen.add(entry["id"])
            save_state(state)
            print(f"Enviado: {entry['title']}")

        if not new_matches:
            print("Sin mini-PC nuevos por debajo de 100 €")

    if TEST_MODE:
        telegram_send(
            "Prueba correcta del bot de Chollometro.\n\n"
            "Filtro activo: mini-PC para Home Assistant por menos de 100 €."
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
