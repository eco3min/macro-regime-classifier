"""
Droits des sources amont — conditions qui doivent voyager avec le fichier.

FRED redistribue certaines series sous le marqueur « Copyrighted: Citation
Required » : la permission d'origine est accordee a FRED, elle ne se
sous-licencie pas. Les conditions du producteur suivent la donnee jusqu'au
fichier telecharge, pas seulement jusqu'a la page dataset — d'ou l'onglet
« Source » dans le XLSX et le bloc `attribution` dans le meta JSON.

Deux regimes en jeu ici :

  imf-pcps / imf-ifs
      IMF Terms and Conditions for the Use of IMF Data, section « The Use of
      IMF Data » (en vigueur depuis le 11 octobre 2024). Telechargement, copie,
      oeuvres derivees, publication et distribution sont autorises, y compris
      quand la donnee a ete obtenue « from another party » — donc via FRED —
      sous trois conditions : attribution au FMI avec lien vers la base ;
      preservation de l'integrite, toute transformation materielle devant etre
      declaree ; transmission de ces memes conditions aux utilisateurs en aval.
      Cette derniere obligation interdit toute sous-licence Creative Commons.

  boe-ogl
      Bank of England, base IADB : Open Government Licence v3.0 (page
      bankofengland.co.uk/legal). Redistribution libre, attribution obligatoire.

  coinbase-btc / coinbase-eth
      Coinbase BTC-USD et ETH-USD, series FRED CBBTCUSD et CBETHUSD, statut
      « Copyrighted: Citation Required » (lu le 17/09/2026). Usage commercial et
      affichage autorises par FRED avec attribution a Coinbase ET a FRED ; pas de
      sous-licence CC BY. Remplacent CoinGecko, dont les API Terms (§4.1.6, §6.2)
      interdisent la redistribution des donnees.

  oecd-mei
      Licence par defaut CC BY 4.0 (politique Open by Default de l'OCDE).
      Redistribution libre, attribution a l'OCDE obligatoire.

  chicago-fed / stlouis-fed / ny-fed / dallas-fed
      Series de Reserve Banks au statut FRED « Copyrighted: Citation Required »
      (NFCI, CFNAI ; T10Y2Y, T10Y3M, T5YIE, T10YIE, T5YIFR ; RRPONTSYD ;
      PCETRIM12M159SFRBDAL — lus le 25/09/2026).
      Meme regime que Coinbase : attribution a la source ET a FRED, pas de CC BY.

Le pendant cote site vit dans les snippets Code Snippets 36 et 114
(`eco3_source_rights()`), qui portent les memes chaines dans le JSON-LD.
"""

SOURCE_RIGHTS = {
    "imf-pcps": {
        "holder": "International Monetary Fund",
        "database": "IMF Primary Commodity Price System",
        "database_url": "https://www.imf.org/en/Research/commodity-prices",
        "attribution": (
            "Source: International Monetary Fund, Primary Commodity Price System, "
            "https://www.imf.org/en/Research/commodity-prices"
        ),
        "terms_url": "https://www.imf.org/en/about/copyright-and-terms",
        "notice": (
            "Redistributed under the IMF Terms and Conditions for the Use of IMF Data. "
            "Attribution to the IMF is required, the integrity of the data must be "
            "preserved, and these same conditions apply to any onward distribution. "
            "Not available under a Creative Commons licence."
        ),
    },
    "imf-ifs": {
        "holder": "International Monetary Fund",
        "database": "IMF International Financial Statistics",
        "database_url": "https://data.imf.org",
        "attribution": (
            "Source: International Monetary Fund, International Financial Statistics, "
            "https://data.imf.org"
        ),
        "terms_url": "https://www.imf.org/en/about/copyright-and-terms",
        "notice": (
            "Redistributed under the IMF Terms and Conditions for the Use of IMF Data. "
            "Attribution to the IMF is required, the integrity of the data must be "
            "preserved, and these same conditions apply to any onward distribution. "
            "Not available under a Creative Commons licence."
        ),
    },
    "oecd-mei": {
        "holder": "Organisation for Economic Co-operation and Development",
        "database": "OECD Main Economic Indicators",
        "database_url": "https://www.oecd.org/en/data.html",
        "attribution": (
            "Source: OECD, Main Economic Indicators, https://www.oecd.org/en/data.html"
        ),
        "terms_url": "https://creativecommons.org/licenses/by/4.0/",
        "notice": (
            "Redistributed under the OECD default licence, Creative Commons "
            "Attribution 4.0. Attribution to the OECD is required."
        ),
    },
    "coinbase-btc": {
        "holder": "Coinbase",
        "database": "Coinbase Bitcoin (CBBTCUSD), retrieved from FRED",
        "database_url": "https://fred.stlouisfed.org/series/CBBTCUSD",
        "attribution": (
            "Source: Coinbase, retrieved from FRED, Federal Reserve Bank of St. Louis, "
            "https://fred.stlouisfed.org/series/CBBTCUSD"
        ),
        "terms_url": "https://fred.stlouisfed.org/legal/#copyright-citation-required",
        "notice": (
            "Produced by Coinbase and retrieved from FRED, where it carries the "
            "\"Copyrighted: Citation required\" status. FRED allows commercial use and "
            "display provided attribution is given both to Coinbase and to FRED. "
            "Not available under a Creative Commons licence: anyone reusing this file "
            "remains bound by the FRED terms."
        ),
    },
    "coinbase-eth": {
        "holder": "Coinbase",
        "database": "Coinbase Ethereum (CBETHUSD), retrieved from FRED",
        "database_url": "https://fred.stlouisfed.org/series/CBETHUSD",
        "attribution": (
            "Source: Coinbase, retrieved from FRED, Federal Reserve Bank of St. Louis, "
            "https://fred.stlouisfed.org/series/CBETHUSD"
        ),
        "terms_url": "https://fred.stlouisfed.org/legal/#copyright-citation-required",
        "notice": (
            "Produced by Coinbase and retrieved from FRED, where it carries the "
            "\"Copyrighted: Citation required\" status. FRED allows commercial use and "
            "display provided attribution is given both to Coinbase and to FRED. "
            "Not available under a Creative Commons licence: anyone reusing this file "
            "remains bound by the FRED terms."
        ),
    },
    # BCE — ECB Data Portal (disclaimer, section Copyright, lu le 2026-09-19) :
    # libre avec citation de la source, reproduction fidele, modifications
    # signalees ; aucun droit de sous-licencier -> jamais CC BY. Miroir PHP :
    # eco3_ecb_source_rights() dans le snippet 50 (repli local), cle `ecb`
    # attendue dans eco3_source_rights() du snippet 114.
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
    "boe-ogl": {
        "holder": "Bank of England",
        "database": "Bank of England Interactive Database (IADB)",
        "database_url": "https://www.bankofengland.co.uk/boeapps/database/",
        "attribution": (
            "Source: Bank of England, Interactive Database, "
            "https://www.bankofengland.co.uk/boeapps/database/"
        ),
        "terms_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "notice": (
            "Contains public sector information licensed under the Open Government "
            "Licence v3.0. Copyright the Governor and Company of the Bank of England."
        ),
    },
    # Series Fed « Copyrighted: Citation required » sur FRED (tags lus par
    # fred_license.py le 2026-09-25). Miroir PHP : cles chicago_fed, stlouis_fed,
    # ny_fed, dallas_fed de eco3_source_rights() (snippet 36), memes chaines.
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
    "ny-fed": {
        "holder": "Federal Reserve Bank of New York",
        "database": "Federal Reserve Bank of New York open market operations data, retrieved from FRED",
        "database_url": "https://www.newyorkfed.org/markets/desk-operations",
        "attribution": (
            "Source: Federal Reserve Bank of New York, retrieved from FRED, "
            "Federal Reserve Bank of St. Louis"
        ),
        "terms_url": "https://fred.stlouisfed.org/legal/#copyright-citation-required",
        "notice": (
            "Produced by the Federal Reserve Bank of New York and retrieved from FRED, "
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
# Verifie serie par serie sur fred.stlouisfed.org le 2026-09-09 : chacune porte
# « Copyrighted: Citation Required ». Une serie absente de cette table n'est PAS
# presumee domaine public : plusieurs series de Reserve Banks regionales (NFCI,
# T10Y2Y, RRPONTSYD…) sont « citation required ». Statut lu par script sur la
# balise series-tag de fred.stlouisfed.org/series/{ID}, jamais de
# memoire ; « pre-approval required » n'entre pas ici, il sort du pipeline.
SERIES_RIGHTS = {
    # IMF — Primary Commodity Price System
    "PALUMUSDM": "imf-pcps",
    "PCOALAUUSDM": "imf-pcps",
    "PCOCOUSDM": "imf-pcps",
    "PCOFFOTMUSDM": "imf-pcps",
    "PCOFFROBUSDM": "imf-pcps",
    "PCOPPUSDM": "imf-pcps",
    "PCOTTINDUSDM": "imf-pcps",
    "PIORECRUSDM": "imf-pcps",
    "PLEADUSDM": "imf-pcps",
    "PMAIZMTUSDM": "imf-pcps",
    "PNGASEUUSDM": "imf-pcps",
    "PNGASJPUSDM": "imf-pcps",
    "PNICKUSDM": "imf-pcps",
    "PPOILUSDM": "imf-pcps",
    "PRICENPQUSDM": "imf-pcps",
    "PRUBBUSDM": "imf-pcps",
    "PSOYBUSDM": "imf-pcps",
    "PSUGAISAUSDM": "imf-pcps",
    "PTEAUSDM": "imf-pcps",
    "PTINUSDM": "imf-pcps",
    "PURANUSDM": "imf-pcps",
    "PWHEAMTUSDM": "imf-pcps",
    "PZINCUSDM": "imf-pcps",
    # IMF — International Financial Statistics
    "INTDSRBRM193N": "imf-ifs",
    # Coinbase (via FRED) — verifie le 17/09/2026
    "CBBTCUSD": "coinbase-btc",
    "CBETHUSD": "coinbase-eth",
    # OCDE — Main Economic Indicators
    "IRLTLT01DEM156N": "oecd-mei",
    "IRLTLT01GBM156N": "oecd-mei",
    "IRLTLT01JPM156N": "oecd-mei",
    # Reserve Banks via FRED — verifie le 25/09/2026 (fred_license.py), miroir
    # des lignes 'rights' du snippet 36
    "NFCI": "chicago-fed",
    "T10Y2Y": "stlouis-fed",
    "T10Y3M": "stlouis-fed",
    "T5YIE": "stlouis-fed",
    "T10YIE": "stlouis-fed",
    "RRPONTSYD": "ny-fed",
    # Hors datasets.json — revue du 25/09/2026 (102 series FRED lues) : series
    # du classifier de regime exportees en standalone, et intrant du score.
    "CFNAI": "chicago-fed",                  # regime : cfnai-national-activity-index
    "PCETRIM12M159SFRBDAL": "dallas-fed",    # regime : trimmed-mean-pce-inflation
    "T5YIFR": "stlouis-fed",                 # score-eco3min (colonne be_5y5y)
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


def rights_for_config(dataset_cfg):
    """Idem depuis une entree de config/datasets.json : `sources[].series` (simple)
    et `input_series` (composite, et entrees « direct series » rangees en composite,
    comme financial-conditions-index)."""
    ids = [
        s.get("series")
        for s in (dataset_cfg.get("sources") or [])
        if isinstance(s, dict) and s.get("series")
    ]
    ids += [sid for sid in (dataset_cfg.get("input_series") or []) if isinstance(sid, str)]
    return rights_for_series(ids)


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
