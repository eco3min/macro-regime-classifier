"""
Droits des sources amont — conditions qui doivent voyager avec le fichier.

FRED redistribue certaines series sous le marqueur « Copyrighted: Citation
Required » : la permission d'origine est accordee a FRED, elle ne se
sous-licencie pas. Les conditions du producteur suivent la donnee jusqu'au
fichier telecharge, pas seulement jusqu'a la page dataset — d'ou l'onglet
« Source » dans le XLSX et le bloc `attribution` dans le meta JSON.

Regimes servis par le classifier de regime :

  ecb
      ECB Data Portal (CISS) : libre avec citation de la BCE, reproduction
      fidele, modifications signalees ; pas de sous-licence Creative Commons.

  chicago-fed / stlouis-fed / dallas-fed
      Series de Reserve Banks au statut FRED « Copyrighted: Citation Required »
      (NFCI, CFNAI ; T10Y2Y, T5YIFR ; PCETRIM12M159SFRBDAL — lus le 25/09/2026).
      Attribution a la source ET a FRED, pas de CC BY.

Copie reduite aux series de ce depot. Une serie absente de SERIES_RIGHTS
n'est pas presumee domaine public : son statut se lit sur sa page FRED.
"""

SOURCE_RIGHTS = {
    # BCE — ECB Data Portal (disclaimer, section Copyright, lu le 2026-09-19) :
    # libre avec citation de la source, reproduction fidele, modifications
    # signalees ; aucun droit de sous-licencier -> jamais CC BY.
    "ecb": {
        "holder": "European Central Bank",
        "database": "ECB Data Portal",
        "database_url": "https://data.ecb.europa.eu",
        "attribution": (
            "Source: European Central Bank, ECB Data Portal, "
            "https://data.ecb.europa.eu"
        ),
        "terms_url": "https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html",
        "notice": (
            "This series is produced by the European Central Bank (ECB Data Portal) "
            "and redistributed here under the ECB's copyright terms: free use provided "
            "the ECB is cited as the source, the data are reproduced accurately, and "
            "any modification (such as a spread or a real rate computed by Eco3min) is "
            "stated explicitly. Eco3min cannot sub-license it under Creative Commons: "
            "anyone reusing this file remains bound by the ECB terms, not by CC BY."
        ),
    },
    # Series Fed « Copyrighted: Citation required » sur FRED (tags lus par
    # FRED le 2026-09-25).
    "chicago-fed": {
        "holder": "Federal Reserve Bank of Chicago",
        "database": "Federal Reserve Bank of Chicago economic indexes, retrieved from FRED",
        "database_url": "https://www.chicagofed.org/research/data",
        "attribution": (
            "Source: Federal Reserve Bank of Chicago, retrieved from FRED, "
            "Federal Reserve Bank of St. Louis"
        ),
        "terms_url": "https://fred.stlouisfed.org/legal/#copyright-citation-required",
        "notice": (
            "Produced by the Federal Reserve Bank of Chicago and retrieved from FRED, "
            "where it carries the \"Copyrighted: Citation required\" status. FRED allows "
            "commercial use and display provided attribution is given both to the "
            "originating source and to FRED. Not available under a Creative Commons "
            "licence: anyone reusing this file remains bound by the FRED terms."
        ),
    },
    "stlouis-fed": {
        "holder": "Federal Reserve Bank of St. Louis",
        "database": "FRED calculated series",
        "database_url": "https://fred.stlouisfed.org",
        "attribution": (
            "Source: Federal Reserve Bank of St. Louis, retrieved from FRED, "
            "Federal Reserve Bank of St. Louis"
        ),
        "terms_url": "https://fred.stlouisfed.org/legal/#copyright-citation-required",
        "notice": (
            "Produced by the Federal Reserve Bank of St. Louis and retrieved from FRED, "
            "where it carries the \"Copyrighted: Citation required\" status. FRED allows "
            "commercial use and display provided attribution is given both to the "
            "originating source and to FRED. Not available under a Creative Commons "
            "licence: anyone reusing this file remains bound by the FRED terms."
        ),
    },
    "dallas-fed": {
        "holder": "Federal Reserve Bank of Dallas",
        "database": "Federal Reserve Bank of Dallas Trimmed Mean PCE inflation rate, retrieved from FRED",
        "database_url": "https://www.dallasfed.org/research/pce",
        "attribution": (
            "Source: Federal Reserve Bank of Dallas, retrieved from FRED, "
            "Federal Reserve Bank of St. Louis"
        ),
        "terms_url": "https://fred.stlouisfed.org/legal/#copyright-citation-required",
        "notice": (
            "Produced by the Federal Reserve Bank of Dallas and retrieved from FRED, "
            "where it carries the \"Copyrighted: Citation required\" status. FRED allows "
            "commercial use and display provided attribution is given both to the "
            "originating source and to FRED. Not available under a Creative Commons "
            "licence: anyone reusing this file remains bound by the FRED terms."
        ),
    },
}

# series_id FRED -> regime de droits. Liste EXPLICITE, pas un motif : un
# `series_id` ne se devine pas, et l'audit doit pouvoir se lire ligne a ligne.
# Verifie serie par serie sur fred.stlouisfed.org le 2026-09-25 : chacune porte
# « Copyrighted: Citation Required ». Une serie absente de cette table n'est PAS
# presumee domaine public : plusieurs series de Reserve Banks regionales (NFCI,
# T10Y2Y, RRPONTSYD…) sont « citation required ». Statut lu par script sur la
# balise series-tag de fred.stlouisfed.org/series/{ID}, jamais de
# memoire ; « pre-approval required » n'entre pas ici, il sort du pipeline.
SERIES_RIGHTS = {
    # Reserve Banks via FRED — statut lu le 25/09/2026
    "NFCI": "chicago-fed",
    "T10Y2Y": "stlouis-fed",
    "CFNAI": "chicago-fed",
    "PCETRIM12M159SFRBDAL": "dallas-fed",
    "T5YIFR": "stlouis-fed",
}


def rights_by_key(key):
    """Rend le bloc de droits depuis sa cle (`rights` du registry v2), ou None."""
    return SOURCE_RIGHTS.get(key) if key else None


def rights_for_series(series_ids):
    """Rend le bloc de droits de la premiere serie sous conditions, ou None."""
    for sid in series_ids or []:
        if sid in SERIES_RIGHTS:
            return SOURCE_RIGHTS[SERIES_RIGHTS[sid]]
    return None


def source_sheet_rows(rights, dataset_id, transform=None):
    """
    Lignes de l'onglet « Source » du XLSX. Deux colonnes, pas de mise en forme :
    ce qui compte est que l'attribution voyage avec le fichier.
    """
    rows = [
        ("Dataset", dataset_id),
        ("Attribution", rights["attribution"]),
        ("Rights holder", rights["holder"]),
        ("Database", rights["database"]),
        ("Database URL", rights["database_url"]),
        ("Terms of use", rights["terms_url"]),
        ("Conditions", rights["notice"]),
    ]
    if transform:
        rows.append(("Transformation", transform))
    rows.append(("Redistributed by", "Eco3min — https://eco3min.fr"))
    return rows


def columns_source_sheet_rows(dataset_id, column_series, transform=None, other=None):
    """
    Onglet « Source » d'une table multi-colonnes dont plusieurs colonnes
    viennent de series sous conditions de detenteurs differents (regime_history).
    column_series : {colonne publiee: series_id FRED}. Seules les series de
    SERIES_RIGHTS sont listees ; les conditions de chaque detenteur une fois.
    """
    rows = [("Dataset", dataset_id)]
    keys = []
    for col, sid in column_series.items():
        key = SERIES_RIGHTS.get(sid)
        if key is None:
            continue
        rows.append(("Column " + col, "FRED " + sid + ". " + SOURCE_RIGHTS[key]["attribution"]))
        if key not in keys:
            keys.append(key)
    for key in keys:
        r = SOURCE_RIGHTS[key]
        rows += [
            ("Rights holder", r["holder"]),
            ("Terms of use", r["terms_url"]),
            ("Conditions", r["notice"]),
        ]
    if other:
        rows.append(("Other columns", other))
    if transform:
        rows.append(("Transformation", transform))
    rows.append(("Redistributed by", "Eco3min — https://eco3min.fr"))
    return rows


def meta_attribution(rights, transform=None):
    """Bloc `attribution` ajoute au meta JSON (objet : ajout non destructif)."""
    block = {
        "attribution": rights["attribution"],
        "rights_holder": rights["holder"],
        "database": rights["database"],
        "database_url": rights["database_url"],
        "terms_url": rights["terms_url"],
        "conditions": rights["notice"],
    }
    if transform:
        block["transformation"] = transform
    return block
