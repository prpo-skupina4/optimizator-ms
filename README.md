# Optimizator mikroservitev

Mikrostoritev izračuna optimalen urnik na podlagi:
- obstoječega urnika uporabnika,
- razpoložljivih terminov,
- uporabnikovih zahtev (prosti dnevi, časovni intervali, pavze).

Rezultat je **nov urnik**, ki vključuje:
- vse **nujne termine** (predavanja ipd.),
- izbrane **vaje**, ki ne povzročajo konfliktov in ustrezajo zahtevam.



## Tehnologije
- Python
- FastAPI
- DFS / backtracking algoritem za optimizacijo



## Zagon z Dockerjem
Predpogoji:
- Docker
- Docker Compose

Zagon mikroservitve:
```bash
docker compose up --build
