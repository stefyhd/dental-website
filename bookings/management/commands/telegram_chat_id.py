"""
Află unde trebuie trimise notificările.

Telegram nu-ți spune „chat id"-ul nicăieri în aplicație. Singurul mod de
a-l afla e să-i scrii botului un mesaj, apoi să întrebi API-ul ce mesaje
a primit. Comanda asta face partea a doua.
"""

from django.core.management.base import BaseCommand

from bookings.telegram import call


class Command(BaseCommand):
    help = "Afișează chat id-urile care au scris botului."

    def handle(self, *args, **options):
        result = call("getUpdates", {"limit": 20}, timeout=10)

        if not result:
            self.stderr.write(
                "Niciun răspuns de la Telegram. Verifică TELEGRAM_BOT_TOKEN."
            )
            return

        if not result.get("ok"):
            self.stderr.write(f"Telegram a refuzat: {result.get('description')}")
            return

        updates = result.get("result", [])

        if not updates:
            self.stdout.write(
                "Nicio conversație găsită.\n\n"
                "Deschide Telegram, caută botul după numele lui de utilizator,\n"
                "apasă Start și scrie-i ceva. Apoi rulează comanda din nou."
            )
            return

        seen = {}

        for update in updates:
            message = update.get("message") or update.get("channel_post") or {}
            chat = message.get("chat") or {}

            if chat.get("id") and chat["id"] not in seen:
                seen[chat["id"]] = chat

        self.stdout.write("Conversații găsite:\n")

        for chat_id, chat in seen.items():
            name = " ".join(filter(None, [
                chat.get("first_name"),
                chat.get("last_name"),
                chat.get("title"),
            ])) or chat.get("username", "")

            self.stdout.write(f"  {chat_id}  {name} ({chat.get('type')})")

        self.stdout.write(
            "\nPune numărul potrivit în variabila de mediu TELEGRAM_CHAT_ID."
        )