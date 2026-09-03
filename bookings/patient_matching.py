"""
Potrivirea numelor de pacienți.

Două reguli, amândouă stricte:

1. CONTOPIM AUTOMAT doar când e sigur: aceleași cuvinte, altă ordine sau
   altă scriere. „Prodan Ana”, „ANA PRODAN” și „Ana Prodan” sunt același
   om. Orice altceva — inclusiv o singură literă diferită — primește fișă
   nouă. „Ioan Radu” și „Ioana Radu” diferă printr-o literă și sunt tată
   și fiică; nu există prag care să separe asta de o greșeală de tastare.

2. NU ÎNTREBĂM NICIODATĂ PACIENTUL. A-i arăta „ai vrut să scrii Ana Maria
   Prodan?” înseamnă a dezvălui numele altui pacient — și faptul că e
   pacient la cabinetul ăsta — unui vizitator neautentificat. Date de
   sănătate către un terț. Asemănările le vede doar medicul, în fișă.
"""

from collections import Counter

from rapidfuzz import fuzz

from .models import Patient
from .text_utils import name_tokens, normalize_text


# Peste cât considerăm două fișe „foarte asemănătoare” în fișa medicului.
VERY_SIMILAR = 85
SIMILAR = 70


def is_same_person(first, second):
    """
    Sunt sigur aceeași persoană?

    Doar dacă au exact aceleași cuvinte. Mulțimile ignoră ordinea, iar
    normalizarea ignoră majusculele și diacriticele — deci acoperă exact
    cele două cazuri sigure: nume inversat și scriere diferită.
    """
    first_tokens = name_tokens(first)

    return bool(first_tokens) and first_tokens == name_tokens(second)


def find_same_person(name, phone):
    """
    Fișa aceleiași persoane de pe numărul acesta, sau None.

    Nu întoarce „posibile potriviri”. Dacă nu e sigur, e None și se creează
    fișă nouă — asemănarea o rezolvă medicul ulterior.
    """
    if not phone:
        return None

    for candidate in Patient.objects.filter(phone=phone):
        if is_same_person(name, candidate.name):
            return candidate

    return None


def similarity_score(first, second):
    """Cât de asemănătoare sunt două nume, 0-100. Doar pentru medic."""
    return fuzz.token_sort_ratio(normalize_text(first), normalize_text(second))


def rank_similar(patient, others):
    """
    Ceilalți de pe același număr, ordonați după cât seamănă cu `patient`.

    Ce vede medicul în fișa „Ana Prodan”:
        Ana Maria Prodan   77   asemănător
        An Marie Prodae    72   asemănător
        Radu Prodan        57   —

    Primele două sunt candidați de contopire; al treilea e clar altcineva
    din familie. Medicul decide, codul doar ordonează.
    """
    ranked = []

    for other in others:
        score = similarity_score(patient.name, other.name)

        if score >= VERY_SIMILAR:
            label = "foarte asemănător"
        elif score >= SIMILAR:
            label = "asemănător"
        else:
            label = ""

        ranked.append({
            "patient": other,
            "score": score,
            "label": label,
        })

    ranked.sort(key=lambda item: -item["score"])

    return ranked


def family_label(patients):
    """
    Numele grupului: 'Fam. Prodan'.

    Numele de familie e cuvântul care apare la CEI MAI MULȚI membri — nu
    la toți. Diferența contează: dacă o fișă are numele scris greșit
    („An Marie Prodae”), cerința „la toți” nu mai găsește nimic și grupul
    ar rămâne fără etichetă. Majoritatea rezistă la un typo.

    Ordinea nume/prenume nu contează, pentru că lucrăm cu mulțimi. La
    egalitate luăm cuvântul mai lung — între „popescu” și „ion”, numele
    de familie e aproape sigur cel lung.

    Pentru un singur pacient întoarcem șir gol: „Fam. X” peste un singur
    om ar dubla numele afișat imediat dedesubt.
    """
    if len(patients) < 2:
        return ""

    counts = Counter()

    for patient in patients:
        counts.update(name_tokens(patient.name))

    # Cel puțin doi membri trebuie să împartă cuvântul, altfel nu e nume
    # de familie, ci doar prenumele cuiva.
    shared = [token for token, count in counts.items() if count >= 2]

    if not shared:
        return "Familie"

    surname = max(shared, key=lambda token: (counts[token], len(token)))

    # Îl afișăm cu diacriticele și majuscula din fișa reală, nu normalizat.
    for patient in patients:
        for word in patient.name.split():
            if normalize_text(word) == surname:
                return f"Fam. {word}"

    return f"Fam. {surname.capitalize()}"


def group_by_phone(patients):
    """
    Grupează fișele după număr de telefon — același număr, aceeași familie.

    Întoarce {phone, label, members, is_family}. Un singur pacient pe un
    număr rămâne un grup cu `label` gol și `is_family` fals, ca pagina
    să-l afișeze ca rând simplu.
    """
    groups = {}

    for patient in patients:
        groups.setdefault(patient.phone, []).append(patient)

    result = []

    for phone, members in groups.items():
        members.sort(key=lambda patient: patient.name)

        result.append({
            "phone": phone,
            "label": family_label(members),
            "members": members,
            "is_family": len(members) > 1,
        })

    result.sort(key=lambda group: normalize_text(group["members"][0].name))

    return result