"""
Normalizare de text pentru căutări și comparații.

Textul original NU se modifică niciodată. Normalizarea se folosește doar
ca să comparăm două șiruri; în baza de date se salvează exact ce a scris
pacientul, cu diacritice și cu majusculele lui.
"""

import unicodedata


def normalize_text(value):
    """
    'Ștefănescu Ana' -> 'stefanescu ana'

    NFKD desparte litera de semnul diacritic ('ș' devine 's' + virgulă),
    apoi aruncăm semnele. Așa merge pentru toate diacriticele românești
    (ă â î ș ț) fără să le enumerăm.
    """
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))

    return " ".join(text.split())


def name_tokens(name):
    """
    'Ana Maria Popescu' -> frozenset({'ana', 'maria', 'popescu'})

    Mulțime, nu listă: ordinea dispare, deci 'Popescu Ana' și 'Ana Popescu'
    devin identice. Cuvintele de o literă (inițiale) se ignoră.
    """
    return frozenset(
        token
        for token in normalize_text(name).split()
        if len(token) > 1
    )