"""
Notificări pe Telegram, când vine o cerere nouă de programare.

DE CE TELEGRAM: mesajul ajunge instant pe telefon, e gratis și nu are
probleme de livrare ca emailul sau SMS-ul.

CE TRIMITEM ȘI DE CE ATÂT: doar ziua, ora și categoria bifată de pacient
(dacă a bifat). Fără nume, fără telefon, fără descrierea scrisă de el.

Motivul nu e pudoare, e juridic: numele plus descrierea a ce-l doare sunt
date medicale identificabile — categorie specială sub GDPR — iar Telegram
e un procesator din afara UE cu care cabinetul n-are niciun contract. O
dată, o oră și „Chirurgie orală" nu identifică pe nimeni care n-are deja
agenda cabinetului în față.

Dacă trimiterea eșuează, programarea NU se pierde. Notificarea e un
lucru în plus, nu o condiție — pacientul trebuie să-și primească
confirmarea chiar dacă Telegram e picat.
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.urls import reverse


logger = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"

# Cât așteptăm răspunsul Telegram. Apelul se face în timpul cererii
# pacientului, deci nu poate dura oricât — patru secunde e limita peste
# care omul simte că pagina s-a blocat.
TIMEOUT = 4


def recipients():
    """
    Cine primește notificările.

    `TELEGRAM_CHAT_ID` acceptă un singur id sau mai multe separate prin
    virgulă, ca să meargă toate variantele fără cod nou:

      "123456789"                 doar un om
      "123456789,987654321"       tu și medicul, fiecare în privat
      "-1001234567890"            un grup — id-urile de grup sunt negative

    Un bot, oricâți destinatari. Botul e cine trimite, chat id-ul e cui.
    """
    raw = getattr(settings, "TELEGRAM_CHAT_ID", "")
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def is_configured():
    """Avem și token, și cel puțin un destinatar? Altfel funcția tace."""
    return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "") and recipients())


def call(method, payload, timeout=TIMEOUT):
    """
    Un apel către API-ul Telegram. Întoarce răspunsul sau None.

    Nu aruncă niciodată: cine o cheamă e pe drumul unei cereri de la
    pacient, iar o eroare de rețea n-are voie să strice o programare.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")

    if not token:
        return None

    request = urllib.request.Request(
        API.format(token=token, method=method),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        # Telegram pune motivul real în corpul răspunsului, nu în cod.
        detail = error.read().decode("utf-8", "replace")[:300]
        logger.warning("Telegram %s a răspuns %s: %s", method, error.code, detail)

    except Exception as error:
        logger.warning("Telegram %s a eșuat: %s", method, error)

    return None


def send_message(text, chat_id=None):
    """
    Trimite mesajul tuturor destinatarilor.

    Telegram n-are „trimite la mai mulți" — API-ul primește un singur
    chat id per apel. Deci doi oameni înseamnă două apeluri, de-aia e
    buclă aici.

    Întoarce True dacă a ajuns la cel puțin unul. Un destinatar picat
    (a blocat botul, a ieșit din grup) nu-i împiedică pe ceilalți să
    primească — bucla merge mai departe, nu se oprește la prima eroare.

    `chat_id` explicit trimite doar acolo, ignorând lista. Folosit de
    comanda de test, ca să poată verifica fiecare destinatar separat.
    """
    targets = [chat_id] if chat_id else recipients()

    if not targets:
        return False

    sent = False

    for target in targets:
        result = call("sendMessage", {
            "chat_id": target,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })

        if result and result.get("ok"):
            sent = True
        else:
            logger.warning("Telegram: mesajul n-a ajuns la %s", target)

    return sent


def dashboard_link():
    """
    Linkul către panou, dacă știm pe ce domeniu stă site-ul.

    Cât timp site-ul e doar local, `SITE_URL` e gol și linkul lipsește —
    un „http://127.0.0.1:8000" trimis pe telefon n-ar duce nicăieri.
    """
    base = getattr(settings, "SITE_URL", "").rstrip("/")

    if not base:
        return ""

    return base + reverse("dashboard_home")


def format_request(appointment):
    """
    Textul notificării.

    Atenție la ce NU e aici: `appointment.patient` și `appointment.notes`
    nu apar deloc, intenționat. Vezi explicația din capul fișierului.
    """
    from django.utils import formats

    when = formats.date_format(appointment.date, "l, j F")

    if appointment.category:
        what = appointment.category.name
    else:
        what = "Fără categorie — vezi descrierea în panou"

    lines = [
        "<b>Cerere nouă de programare</b>",
        "",
        f"{when} · {appointment.time:%H:%M}",
        what,
    ]

    link = dashboard_link()
    if link:
        lines += ["", f'<a href="{link}">Confirmă din panou</a>']

    return "\n".join(lines)


def notify_new_request(appointment):
    """Cheamă asta după ce s-a salvat o cerere. Tace dacă nu e configurat."""
    if not is_configured():
        return False

    return send_message(format_request(appointment))