from typing import List, Optional
from pydantic import BaseModel
from datetime import time


class Predmet(BaseModel):
    predmet_id: int
    oznaka: str
    ime: str
    
class Aktivnost(BaseModel):
    aktivnost_id: Optional[int] = None
    oznaka: str
    ime:str

class Termin(BaseModel):
    termin_id: Optional[int] = None
    zacetek: time
    dolzina: int
    dan:int
    lokacija: str
    tip:str
    predmet: Optional[Predmet] = None
    aktivnost: Optional[Aktivnost] = None


class Urnik(BaseModel):
    uporabnik_id: int #ali rabim userja ali samo njegov id?
    termini: List[Termin]

class Pavza(BaseModel):
    zacetek:time
    dolzina: int
    dan:int

class VajeZahteva(BaseModel):#zahteva je samo za vaje
    predmet: Predmet
    zacetek: Optional[time] = None
    konec: Optional[time] = None
    dan: int

class Zahteve(BaseModel):
    prosti_dnevi: List[int]
    zacetek: Optional[time] = None #pouka
    konec: Optional[time] = None
    pavze: List[Pavza]
    vaje:List[VajeZahteva]
    min_pavze: bool = False

class OptimizeRequest(BaseModel):
    uporabnik_id: int
    urnik: Urnik
    zahteve: Zahteve
    termini:List[Termin]#vsi možni termini predmetov + dogodkov