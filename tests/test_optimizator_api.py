# tests/test_optimizator_api.py
import pytest
from datetime import time
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api.optimizator import optimizator
from app.api.models import Predmet, Aktivnost, Termin


def J(m):
    """Pydantic -> JSON-serializable dict (time -> 'HH:MM:SS')"""
    return m.model_dump(mode="json")


def mk_predmet(pid: int, oznaka="PRPO", ime="Projekt") -> Predmet:
    return Predmet(predmet_id=pid, oznaka=oznaka, ime=ime)


def mk_termin(
    tid: int,
    dan: int,
    hh: int,
    mm: int,
    dolzina: int,
    tip: str,
    predmet: Predmet | None = None,
    aktivnost: Aktivnost | None = None,
    lokacija="P1",
) -> Termin:
    return Termin(
        termin_id=tid,
        dan=dan,
        zacetek=time(hh, mm),
        dolzina=dolzina,
        lokacija=lokacija,
        tip=tip,
        predmet=predmet,
        aktivnost=aktivnost,
    )


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(optimizator, prefix="/optimizacije")
    return app


@pytest.mark.anyio
async def test_health_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/optimizacije/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_returns_empty_if_mandatory_terms_overlap(app):
    # 2 nujna termina (P) se križata -> urnik []
    uid = 631234
    p = mk_predmet(1)
    t1 = mk_termin(1, dan=1, hh=9, mm=0, dolzina=90, tip="P", predmet=p)
    t2 = mk_termin(2, dan=1, hh=9, mm=30, dolzina=90, tip="P", predmet=p)  # overlap

    req = {
        "uporabnik_id": uid,
        "urnik": {"uporabnik_id": uid, "termini": [J(t1), J(t2)]},
        "zahteve": {"prosti_dnevi": [], "zacetek": None, "konec": None, "pavze": [], "vaje": [], "min_pavze": False},
        "termini": [],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/optimizacije/", json=req)

    assert r.status_code == 200
    data = r.json()
    assert data["uporabnik_id"] == uid
    assert data["termini"] == []


@pytest.mark.anyio
async def test_respects_prosti_dnevi(app):
    uid = 1
    p = mk_predmet(1)
    t1 = mk_termin(1, dan=2, hh=10, mm=0, dolzina=90, tip="P", predmet=p)

    req = {
        "uporabnik_id": uid,
        "urnik": {"uporabnik_id": uid, "termini": [J(t1)]},
        "zahteve": {"prosti_dnevi": [2], "zacetek": None, "konec": None, "pavze": [], "vaje": [], "min_pavze": False},
        "termini": [],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/optimizacije/", json=req)

    assert r.status_code == 200
    assert r.json()["termini"] == []


@pytest.mark.anyio
async def test_respects_start_end_time_window(app):
    uid = 1
    p = mk_predmet(1)
    t1 = mk_termin(1, dan=1, hh=8, mm=0, dolzina=90, tip="P", predmet=p)

    req = {
        "uporabnik_id": uid,
        "urnik": {"uporabnik_id": uid, "termini": [J(t1)]},
        "zahteve": {"prosti_dnevi": [], "zacetek": "09:00:00", "konec": None, "pavze": [], "vaje": [], "min_pavze": False},
        "termini": [],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/optimizacije/", json=req)

    assert r.status_code == 200
    assert r.json()["termini"] == []


@pytest.mark.anyio
async def test_respects_pavza_block(app):
    uid = 1
    p = mk_predmet(1)
    t1 = mk_termin(1, dan=1, hh=12, mm=0, dolzina=60, tip="P", predmet=p)

    req = {
        "uporabnik_id": uid,
        "urnik": {"uporabnik_id": uid, "termini": [J(t1)]},
        "zahteve": {
            "prosti_dnevi": [],
            "zacetek": None,
            "konec": None,
            "pavze": [{"zacetek": "12:30:00", "dolzina": 30, "dan": 1}],
            "vaje": [],
            "min_pavze": False,
        },
        "termini": [],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/optimizacije/", json=req)

    assert r.status_code == 200
    assert r.json()["termini"] == []
