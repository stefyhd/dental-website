"""
Trimite un mesaj de probă, ca să vezi că legătura merge înainte să
depinzi de ea la o programare adevărată.

Testează fiecare destinatar separat, nu toți deodată. Cu doi oameni pe
listă, „a plecat" nu spune nimic util: poate a plecat doar la tine, iar
medicul n-a apăsat Start la bot și n-o să afle niciodată.
"""

from django.core.management.base import BaseCommand

from bookings.telegram import recipients, send_message


TEXT = "<b>Test</b>\n\nDacă vezi mesajul ăsta, notificările merg."


class Command(BaseCommand):
    help = "Trimite un mesaj de test pe Telegram, fiecărui destinatar în parte."

    def handle(self, *args, **options):
        from django.conf import settings

        if not getattr(settings, "TELEGRAM_BOT_TOKEN", ""):
            self.stderr.write(
                "Lipsește TELEGRAM_BOT_TOKEN.\n"
                "Notificările sunt oprite — site-ul funcționează normal,\n"
                "doar că nu te anunță nimeni."
            )
            return

        targets = recipients()

        if not targets:
            self.stderr.write(
                "Lipsește TELEGRAM_CHAT_ID.\n"
                "Rulează `python manage.py telegram_chat_id` ca să-l afli."
            )
            return

        self.stdout.write(f"Destinatari configurați: {len(targets)}\n")

        failed = []

        for target in targets:
            if send_message(TEXT, chat_id=target):
                self.stdout.write(self.style.SUCCESS(f"  {target}  trimis"))
            else:
                self.stdout.write(self.style.ERROR(f"  {target}  NU a plecat"))
                failed.append(target)

        if not failed:
            self.stdout.write(
                self.style.SUCCESS("\nToți au primit. Verificați telefoanele.")
            )
            return

        self.stderr.write(
            f"\n{len(failed)} din {len(targets)} n-au primit. Cauze uzuale:\n"
            "  · chat id-ul e greșit (verifică-l cu telegram_chat_id)\n"
            "  · omul n-a apăsat Start la bot — Telegram nu lasă botul să\n"
            "    scrie primul cuiva care nu i-a vorbit niciodată\n"
            "  · era un grup și s-a transformat în supergrup, deci id-ul\n"
            "    s-a schimbat (începe cu -100)\n"
            "  · botul a fost scos din grup"
        )