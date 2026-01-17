# tests/test_optimizator_selection.py
import pytest
from datetime import time
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.optimizator import optimizator 
from app.api.models import Predmet, Termin 


def mk_predmet(pid: int, oznaka: str) -> Predmet:
    return Predmet(predmet_id=pid, oznaka=oznaka, ime=oznaka)

def mk_termin(tid: int, dan: int, hh: int, mm: int, dolzina: int, tip: str, predmet: Predmet) -> Termin:
    return Termin(
        termin_id=tid,
        dan=dan,
        zacetek=time(hh, mm),
        dolzina=dolzina,
        lokacija="P1",
        tip=tip,
        predmet=predmet,
        aktivnost=None
    )

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(optimizator, prefix="/optimizacije")
    return app

@pytest.mark.anyio
async def test_picks_one_exercise_per_subject_when_possible(app):
    # 2 predmeta, vsak ima 2 možna termina za LV -> izbrati mora po 1 iz vsake skupine.
    p1 = mk_predmet(1, "PRPO")
    p2 = mk_predmet(2, "OSA")

    # kandidati (req.termini)
    prpo_a = mk_termin(101, dan=2, hh=10, mm=0, dolzina=90, tip="LV", predmet=p1)
    prpo_b = mk_termin(102, dan=2, hh=12, mm=0, dolzina=90, tip="LV", predmet=p1)
    osa_a  = mk_termin(201, dan=3, hh=10, mm=0, dolzina=90, tip="LV", predmet=p2)
    osa_b  = mk_termin(202, dan=3, hh=12, mm=0, dolzina=90, tip="LV", predmet=p2)

    req = {
        "uporabnik_id": 1,
        "urnik": {"uporabnik_id": 1, "termini": []},  # brez nujnih
        "zahteve": {
            "prosti_dnevi": [],
            "zacetek": None,
            "konec": None,
            "pavze": [],
            "vaje": [
                {"predmet": p1.model_dump(mode="json"), "zacetek": None, "konec": None, "dan": 2},
                {"predmet": p2.model_dump(mode="json"), "zacetek": None, "konec": None, "dan": 3},
            ],
            "min_pavze": False,
        },
        "termini": [
            prpo_a.model_dump(mode="json"),
            prpo_b.model_dump(mode="json"),
            osa_a.model_dump(mode="json"),
            osa_b.model_dump(mode="json"),
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/optimizacije/", json=req)

    print(r.status_code, r.json())

    assert r.status_code == 200
    termini = r.json()["termini"]
    assert len(termini) == 2
    assert {t["predmet"]["predmet_id"] for t in termini} == {1, 2}


def J(m):
    return m.model_dump(mode="json")

@pytest.mark.anyio
async def test_min_pavze_prefers_smaller_gaps(app):
    p1 = mk_predmet(1, "PRPO")
    p2 = mk_predmet(2, "OSA")

    prpo_early = mk_termin(101, dan=2, hh=10, mm=0, dolzina=90, tip="LV", predmet=p1)
    prpo_late  = mk_termin(102, dan=2, hh=16, mm=0, dolzina=90, tip="LV", predmet=p1)
    osa_mid    = mk_termin(201, dan=2, hh=12, mm=0, dolzina=90, tip="LV", predmet=p2)

    uid = 1
    req = {
        "uporabnik_id": uid,
        "urnik": {"uporabnik_id": uid, "termini": []},
        "zahteve": {
            "prosti_dnevi": [],
            "zacetek": None,
            "konec": None,
            "pavze": [],
            "vaje": [
                {"predmet": J(p1), "zacetek": None, "konec": None, "dan": 2},
                {"predmet": J(p2), "zacetek": None, "konec": None, "dan": 2},
            ],
            "min_pavze": True,
        },
        "termini": [J(prpo_early), J(prpo_late), J(osa_mid)],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/optimizacije/", json=req)

    assert r.status_code == 200
    termini = r.json()["termini"]
    assert len(termini) == 2

    # Pri min_pavze pričakujemo PRPO 10:00 + OSA 12:00 (manjša luknja)
    starts = {t["predmet"]["predmet_id"]: t["zacetek"] for t in termini}
    assert starts[1] == "10:00:00"   # PRPO early
    assert starts[2] == "12:00:00"   # OSA mid
