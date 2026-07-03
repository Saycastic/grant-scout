"""
Тест доступности новых источников. Проверяем URL через httpx, фиксируем статус.
"""
import sys, os
sys.path.insert(0, "/root/grant-scout")

import httpx
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}

NEW_SOURCES = [
    ("guggenheim_foundation", "https://www.gf.org/applicants/the-fellowship/"),
    ("nea_grants", "https://www.arts.gov/grants"),
    ("kresge_arts", "https://kresge.org/programs/arts-culture/"),
    ("rauschenberg_foundation", "https://www.rauschenbergfoundation.org/grants"),
    ("joan_mitchell_foundation", "https://www.joanmitchellfoundation.org/grants"),
    ("jerome_foundation", "https://www.jeromefdn.org/apply"),
    ("harpo_foundation", "https://www.harpofoundation.org/apply/"),
    ("arts_council_england", "https://www.artscouncil.org.uk/funding/grants-arts-individuals"),
    ("creative_scotland", "https://www.creativescotland.com/funding/funding-programmes/open-fund-individuals"),
    ("arts_council_wales", "https://arts.wales/funding"),
    ("jerwood_arts", "https://jerwoodarts.org/funding/"),
    ("freelands_foundation", "https://www.freelandsfoundation.co.uk/"),
    ("mondriaan_fund", "https://www.mondriaanfund.nl/en/grants/"),
    ("kulturradet_sweden", "https://www.kulturradet.se/bidrag/"),
    ("arts_council_norway", "https://www.kulturradet.no/stotteordninger/"),
    ("cnap_france", "https://www.cnap.fr/aides-aux-artistes"),
    ("kulturstiftung_des_bundes", "https://www.kulturstiftung-bund.de/en/funding.html"),
    ("prince_claus_fund", "https://www.princeclausfund.org/grants"),
    ("goethe_institut_grants", "https://www.goethe.de/en/kul/the/res.html"),
    ("eflux_opportunities", "https://www.e-flux.com/announcements/"),
    ("callforentry", "https://www.callforentry.org/"),
    ("nyfa_source", "https://www.nyfa.org/grants-and-fellowships/"),
    ("resartis", "https://www.resartis.org/residencies/"),
    ("skowhegan_school", "https://www.skowheganart.org/program/"),
    ("yaddo_residency", "https://yaddo.org/apply/"),
    ("vermont_studio_center", "https://www.vermontstudiocenter.org/fellowships"),
    ("iscp_new_york", "https://www.iscp-nyc.org/residency/"),
    ("headlands_center", "https://www.headlands.org/program/artist-in-residence/"),
    ("australia_council", "https://australiacouncil.gov.au/funding/"),
    ("creative_new_zealand", "https://www.creativenz.govt.nz/funding-and-support"),
    ("japan_foundation_grants", "https://www.jpf.go.jp/e/program/arts.html"),
    ("asia_art_archive", "https://aaa.org.hk/en/grants"),
    ("fonca_mexico", "https://fonca.cultura.gob.mx/becas/"),
    ("fna_argentina", "https://www.fnartes.gov.ar/becas"),
    ("african_arts_trust", "https://www.africanartstrust.org/grants/"),
    ("smithsonian_african_art", "https://africa.si.edu/research/fellowships/"),
    ("cy_twombly_foundation", "https://cytwomblyfoundation.org/grants/"),
    ("louis_comfort_tiffany", "https://www.lctf.org/"),
    ("macarthur_foundation_arts", "https://www.macfound.org/programs/arts/"),
    ("pew_fellowships", "https://www.pewtrusts.org/en/projects/pew-fellows"),
    ("map_fund", "https://mapfund.org/grants/"),
    ("art_matters_foundation", "https://www.artmattersfoundation.org/grants"),
    ("canada_council_arts", "https://canadacouncil.ca/funding/grants/visual-arts"),
    ("arts_council_ireland", "https://www.artscouncil.ie/Funds/"),
    ("danish_arts_foundation", "https://www.kunst.dk/english/grants/"),
    ("finnish_arts_agency", "https://www.taike.fi/en/grants"),
    ("creative_europe", "https://culture.ec.europa.eu/creative-europe"),
    ("european_cultural_foundation", "https://www.culturalfoundation.eu/grants"),
    ("onassis_foundation", "https://www.onassis.org/scholarships/"),
    ("arts_council_korea", "https://www.arko.or.kr/eng/"),
    ("national_arts_council_singapore", "https://www.nac.gov.sg/support/grants"),
    ("india_foundations_grants", "https://indiaifa.org/grants-projects.html"),
    ("ford_foundation_arts", "https://www.fordfoundation.org/work/challenging-inequality/creativity-and-free-expression/"),
    ("alliance_residencies", "https://www.artistcommunities.org/residency-search"),
    ("latinoarte_grants", "https://nalac.org/grants/"),
    ("pro_helvetia_new", "https://prohelvetia.ch/en/funding/"),
    ("wellcome_arts", "https://wellcome.org/grant-funding/schemes/arts-awards"),
    ("arts_council_northern_ireland", "https://artscouncil-ni.org/funding/"),
]

ok = []
fail = []

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=10) as client:
    for sid, url in NEW_SOURCES:
        try:
            resp = client.get(url)
            status = resp.status_code
        except Exception as e:
            status = -1

        if status == 200:
            ok.append((sid, url, status))
            print(f"  ✅ {sid}: {status}")
        else:
            fail.append((sid, url, status))
            print(f"  ❌ {sid}: {status}")

print(f"\n=== {len(ok)} ok / {len(fail)} fail ===")
print("\nOK:")
for sid, url, s in ok:
    print(f"  {sid}")
print("\nFAIL:")
for sid, url, s in fail:
    print(f"  {sid}: {s}")
