from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import time
from fastapi import Request as FastAPIRequest

from app.api.models import Termin, Urnik, OptimizeRequest  # prilagodi, če imaš druga imena


optimizator = APIRouter()


def nujni_termini(urnik: Urnik) -> List[Termin]:
    termini = []
    for t in urnik.termini:
        if (t.tip == "" or t.tip == "P") or (t.aktivnost is not None):
            termini.append(t)
    return termini


def minute(a: time) -> int:
    return a.hour * 60 + a.minute


def krizanje(a: Termin, b: Termin) -> bool:
    if a.dan != b.dan:
        return False
    a_s = minute(a.zacetek)
    a_k = a_s + a.dolzina
    b_s = minute(b.zacetek)
    b_k = b_s + b.dolzina
    return not (a_k <= b_s or b_k <= a_s)


def prosti_dnevi(termini, zahteve) -> bool:
    prosti = set(zahteve.prosti_dnevi or [])
    return all(t.dan not in prosti for t in termini)


def cas(termini, z, k) -> bool:
    if z is not None:
        z_m = minute(z)
        for t in termini:
            if minute(t.zacetek) < z_m:
                return False

    if k is not None:
        k_m = minute(k)
        for t in termini:
            tk = minute(t.zacetek) + t.dolzina
            if tk > k_m:
                return False

    return True


def pavze(termini, zahteve) -> bool:
    # p.dolzina mora biti int (minute)
    for p in zahteve.pavze:
        z = minute(p.zacetek)
        k = z + p.dolzina
        for t in termini:
            if t.dan != p.dan:
                continue
            z2 = minute(t.zacetek)
            k2 = z2 + t.dolzina
            if not (k2 <= z or k <= z2):
                return False
    return True


def zahteveCheck(termini, zahteve) -> bool:
    return (
        prosti_dnevi(termini, zahteve)
        and cas(termini, zahteve.zacetek, zahteve.konec)
        and pavze(termini, zahteve)
    )


def grupiraj(req: OptimizeRequest):
    kandidati = [t for t in req.termini if (t.tip in ("LV", "AV")) and (t.predmet is not None)]
    skupine = []

    for v in req.zahteve.vaje:
        predmet_id = v.predmet.predmet_id
        vaje = []

        for k in kandidati:
            if k.predmet.predmet_id != predmet_id:
                continue
            if k.dan != v.dan:
                continue
            if v.zacetek is not None and k.zacetek < v.zacetek:
                continue
            if v.konec is not None:
                k1 = minute(v.konec)
                k2 = minute(k.zacetek) + k.dolzina
                if k2 > k1:
                    continue

            vaje.append(k)

        skupine.append(vaje)

    return skupine


def min_razlika(t: Termin, izbran) -> int:
    dnevi = [x for x in izbran if x.dan == t.dan]
    if not dnevi:
        return 0
    naj = 10**9
    tz = minute(t.zacetek)
    tk = tz + t.dolzina
    for d in dnevi:
        z = minute(d.zacetek)
        k = z + d.dolzina
        if tk <= z:
            naj = min(naj, z - tk)
        elif k <= tz:
            naj = min(naj, tz - k)
        else:
            naj = 0
    return naj


def _total_gaps_minutes(termini: List[Termin]) -> int:
    total = 0
    for d in set(t.dan for t in termini):
        day = sorted([t for t in termini if t.dan == d], key=lambda x: minute(x.zacetek))
        if len(day) <= 1:
            continue
        intervals = [(minute(t.zacetek), minute(t.zacetek) + t.dolzina) for t in day]
        cur_end = intervals[0][1]
        for s, e in intervals[1:]:
            if s > cur_end:
                total += (s - cur_end)
            cur_end = max(cur_end, e)
    return total


def dodaj(t: Termin, nujno: List[Termin], izbran: List[Termin]) -> bool:
    for x in nujno + izbran:
        if krizanje(t, x):
            return False
    return True


@optimizator.post("/{uporabnik_id}", response_model=Urnik)
async def optimizacije(uporabnik_id: int, req: OptimizeRequest, request: FastAPIRequest):
    # konsistenca user id
    if req.uporabnik_id != uporabnik_id:
        raise HTTPException(400, detail="uporabnik_id v poti in body se ne ujemata")

    zahteve = req.zahteve
    nujno = nujni_termini(req.urnik)

    # 1) nujni termini se ne smejo križati
    for i in range(len(nujno)):
        for j in range(i + 1, len(nujno)):
            if krizanje(nujno[i], nujno[j]):
                return Urnik(uporabnik_id=req.uporabnik_id, termini=[])

    # 2) nujni termini morajo ustrezati zahtevam
    if not zahteveCheck(nujno, zahteve):
        return Urnik(uporabnik_id=req.uporabnik_id, termini=[])

    # 3) če uporabnik sploh ne želi nobenih vaj → vrnemo samo nujne
    if not (zahteve.vaje and len(zahteve.vaje) > 0):
        nujno_sorted = sorted(nujno, key=lambda t: (t.dan, minute(t.zacetek)))
        return Urnik(uporabnik_id=req.uporabnik_id, termini=nujno_sorted)

    # 4) zgradi skupine kandidatov po zahtevah
    skupine = grupiraj(req)
    if any(len(s) == 0 for s in skupine):
        return Urnik(uporabnik_id=req.uporabnik_id, termini=[])

    izbran: List[Termin] = []

    # KLJUČNI FIX: naj_urnik mora biti None, ne []
    naj_urnik: Optional[List[Termin]] = None
    naj_vrednost = 10**18

    # najmanjše skupine najprej
    uredi = sorted(range(len(skupine)), key=lambda idx: len(skupine[idx]))
    skupine = [skupine[i] for i in uredi]

    def dfs(i: int) -> None:
        nonlocal naj_urnik, naj_vrednost

        if i == len(skupine):
            if not zahteveCheck(nujno + izbran, zahteve):
                return

            if zahteve.min_pavze:
                s = _total_gaps_minutes(nujno + izbran)
                if s < naj_vrednost:
                    naj_vrednost = s
                    naj_urnik = izbran[:]
            else:
                # prva najdena rešitev je dovolj
                naj_urnik = izbran[:]
            return

        # če ne optimiziraš pavz, in rešitev že obstaja, končaj
        if (naj_urnik is not None) and (not zahteve.min_pavze):
            return

        skupina = skupine[i]

        if zahteve.min_pavze and (nujno + izbran):
            skupina = sorted(skupina, key=lambda o: min_razlika(o, nujno + izbran))
        else:
            skupina = sorted(skupina, key=lambda t: (t.dan, minute(t.zacetek)))

        for t in skupina:
            if not dodaj(t, nujno, izbran):
                continue

            izbran.append(t)

            if zahteveCheck(nujno + izbran, zahteve):
                if zahteve.min_pavze and (naj_urnik is not None):
                    cur = _total_gaps_minutes(nujno + izbran)
                    if cur <= naj_vrednost:
                        dfs(i + 1)
                else:
                    dfs(i + 1)

            izbran.pop()

    dfs(0)

    if naj_urnik is None:
        return Urnik(uporabnik_id=req.uporabnik_id, termini=[])

    # vrni skupaj: nujni + izbrane vaje
    rezultat = sorted(nujno + naj_urnik, key=lambda t: (t.dan, minute(t.zacetek)))
    return Urnik(uporabnik_id=req.uporabnik_id, termini=rezultat)


@optimizator.get("/health")
def health():
    return {"status": "ok"}
