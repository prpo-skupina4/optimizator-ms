# tests/test_optimizator_helpers.py
from datetime import time

from app.api.optimizator import minute, krizanje, _total_gaps_minutes 
from app.api.models import Termin, Predmet


def mk_term(tid, dan, hh, mm, dolzina):
    p = Predmet(predmet_id=1, oznaka="X", ime="X")
    return Termin(
        termin_id=tid,
        dan=dan,
        zacetek=time(hh, mm),
        dolzina=dolzina,
        lokacija="P1",
        tip="P",
        predmet=p,
        aktivnost=None
    )

def test_minute():
    assert minute(time(0, 0)) == 0
    assert minute(time(1, 30)) == 90

def test_krizanje_true():
    a = mk_term(1, 1, 9, 0, 60)
    b = mk_term(2, 1, 9, 30, 60)
    assert krizanje(a, b) is True

def test_krizanje_false_different_day():
    a = mk_term(1, 1, 9, 0, 60)
    b = mk_term(2, 2, 9, 30, 60)
    assert krizanje(a, b) is False

def test_total_gaps_minutes():
    # dan 1: 09:00-10:00 in 12:00-13:00 -> gap 120 min
    a = mk_term(1, 1, 9, 0, 60)
    b = mk_term(2, 1, 12, 0, 60)
    assert _total_gaps_minutes([a, b]) == 120
