"""
Catalogul de referință al serviciilor stomatologice.

NU este o tabelă în baza de date. Sunt date fixe, versionate în git, folosite
doar ca să sugereze medicului nume de servicii și categoria potrivită atunci
când adaugă un serviciu nou.

Serviciile reale ale cabinetului rămân în tabela `Service` — medicul poate
scrie orice, catalogul doar îi economisește tastatura.
"""

from rapidfuzz import fuzz

from .text_utils import normalize_text


# (slug, nume afișat, ordine)
CATEGORIES = [
    ("consultatii", "Consultații și diagnostic", 10),
    ("profilaxie", "Profilaxie și igienizare", 20),
    ("stomatologie-generala", "Stomatologie generală", 30),
    ("endodontie", "Endodonție", 40),
    ("protetica", "Protetică", 50),
    ("implantologie", "Implantologie", 60),
    ("ortodontie", "Ortodonție", 70),
    ("estetica", "Estetică dentară", 80),
    ("chirurgie", "Chirurgie orală", 90),
    ("urgente", "Urgențe", 100),
]


# (nume, slug categorie, durată în minute)
SERVICES = [
    # Consultații și diagnostic
    ("Consultație stomatologică", "consultatii", 30),
    ("Consultație de specialitate", "consultatii", 30),
    ("Control periodic", "consultatii", 20),
    ("Plan de tratament", "consultatii", 30),
    ("Radiografie dentară retroalveolară", "consultatii", 15),
    ("Radiografie panoramică (OPG)", "consultatii", 20),

    # Profilaxie și igienizare
    ("Detartraj cu ultrasunete", "profilaxie", 40),
    ("Detartraj și periaj profesional", "profilaxie", 60),
    ("Air-flow (periaj cu jet)", "profilaxie", 30),
    ("Igienizare completă", "profilaxie", 60),
    ("Fluorizare", "profilaxie", 20),
    ("Sigilare dentară", "profilaxie", 30),

    # Stomatologie generală
    ("Obturație fizionomică (plombă)", "stomatologie-generala", 45),
    ("Obturație compozit", "stomatologie-generala", 45),
    ("Obturație provizorie", "stomatologie-generala", 20),
    ("Tratament carie simplă", "stomatologie-generala", 45),
    ("Tratament carie profundă", "stomatologie-generala", 60),
    ("Reconstrucție coronară", "stomatologie-generala", 60),
    ("Coafaj pulpar", "stomatologie-generala", 45),

    # Endodonție
    ("Tratament de canal (monoradicular)", "endodontie", 60),
    ("Tratament de canal (pluriradicular)", "endodontie", 90),
    ("Retratament endodontic", "endodontie", 90),
    ("Extirpare pulpară", "endodontie", 60),
    ("Obturație de canal", "endodontie", 60),
    ("Drenaj endodontic", "endodontie", 30),

    # Protetică
    ("Coroană ceramică", "protetica", 60),
    ("Coroană metalo-ceramică", "protetica", 60),
    ("Coroană din zirconiu", "protetica", 60),
    ("Punte dentară", "protetica", 90),
    ("Proteză mobilă acrilică", "protetica", 60),
    ("Proteză scheletată", "protetica", 60),
    ("Proteză parțială", "protetica", 60),
    ("Inlay / Onlay", "protetica", 60),
    ("Amprentă dentară", "protetica", 30),
    ("Reparație proteză", "protetica", 45),

    # Implantologie
    ("Consultație implantologie", "implantologie", 30),
    ("Inserare implant dentar", "implantologie", 90),
    ("Adiție osoasă", "implantologie", 90),
    ("Sinus lift", "implantologie", 120),
    ("Coroană pe implant", "implantologie", 60),
    ("Bont protetic (abutment)", "implantologie", 45),

    # Ortodonție
    ("Consultație ortodontică", "ortodontie", 30),
    ("Aparat dentar fix metalic", "ortodontie", 90),
    ("Aparat dentar fix ceramic", "ortodontie", 90),
    ("Aparat dentar mobilizabil", "ortodontie", 60),
    ("Activare aparat dentar", "ortodontie", 30),
    ("Gutiere transparente", "ortodontie", 60),
    ("Contenție ortodontică", "ortodontie", 45),

    # Estetică dentară
    ("Albire dentară profesională", "estetica", 60),
    ("Albire la domiciliu (gutiere)", "estetica", 45),
    ("Fațete ceramice", "estetica", 90),
    ("Fațete compozit", "estetica", 60),
    ("Remodelare estetică", "estetica", 60),
    ("Bijuterie dentară", "estetica", 30),

    # Chirurgie orală
    ("Extracție dentară simplă", "chirurgie", 45),
    ("Extracție dentară chirurgicală", "chirurgie", 60),
    ("Extracție molar de minte", "chirurgie", 60),
    ("Chiuretaj alveolar", "chirurgie", 45),
    ("Frenectomie", "chirurgie", 45),
    ("Gingivectomie", "chirurgie", 45),
    ("Incizie și drenaj abces", "chirurgie", 30),

    # Urgențe
    ("Urgență stomatologică", "urgente", 30),
    ("Tratament durere acută", "urgente", 30),
    ("Recimentare coroană", "urgente", 30),
    ("Refacere obturație pierdută", "urgente", 30),
]


MINIMUM_SCORE = 70


def match_score(query, name):
    """
    Cât de bine se potrivește ce a tastat medicul cu numele unui serviciu.

    Prefixul cântărește cel mai mult, pentru că omul tastează de la început:
    'consultat' trebuie să ducă la 'Consultație', nu în altă parte.

    Când nu e prefix, comparăm în primul rând cu fiecare CUVÂNT din nume,
    nu cu numele întreg. Motivul, măsurat pe catalogul complet: comparat
    cu numele întreg, 'detrataj' nimerea 'Plan de tratament' (88) și rata
    complet 'Detartraj'. Comparat pe cuvinte, 'detartraj' iese primul.

    Potrivirile pe numele întreg rămân, dar cu pondere mai mică — ele
    salvează cazul invers, cuvântul scurt ('dert'), pe care comparația
    cuvânt-cu-cuvânt îl ratează.

    Măsurat pe 30 de căutări reale, cu și fără typo: 30/30 în primele trei.
    """
    query = normalize_text(query)
    name = normalize_text(name)

    if not query:
        return 0.0

    if name.startswith(query):
        return 100.0

    words = name.split()

    if any(word.startswith(query) for word in words):
        return 95.0

    best_word = max((fuzz.ratio(query, word) for word in words), default=0)

    return max(
        best_word,
        fuzz.partial_ratio(query, name) * 0.9,
        fuzz.token_sort_ratio(query, name) * 0.85,
    )


def suggest_services(query, limit=8):
    """
    Sugestii pentru ce a tastat medicul.

    Întoarce o listă de dicționare: {name, category_slug, duration, score}.
    Cine apelează decide ce face cu `category_slug` — aici nu atingem baza
    de date, ca funcția să rămână testabilă fără Django.
    """
    query = (query or "").strip()

    if len(query) < 2:
        return []

    matches = []

    for name, category_slug, duration in SERVICES:
        score = match_score(query, name)

        if score < MINIMUM_SCORE:
            continue

        matches.append({
            "name": name,
            "category_slug": category_slug,
            "duration": duration,
            "score": score,
        })

    matches.sort(key=lambda item: (-item["score"], item["name"]))

    return matches[:limit]