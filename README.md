# Student Life Dashboard MVP

Prototype local d'un dashboard interactif sur la vie etudiante en region parisienne.

## Contenu

- `app.py` : application Streamlit (carte, KPI, comparaison simple).
- `requirements.txt` : dependances Python.
- `run.command` : lancement rapide sur macOS.

## Lancer le projet

### Option 1 (recommandee): script macOS

Double-cliquer sur `run.command`.

### Option 2: terminal

```bash
cd "/Users/dany/Desktop/student-life-dashboard-mvp"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

Puis ouvrir:

- http://127.0.0.1:8501

## Notes

- Les donnees actuelles sont de demonstration (mock).
- Les prochaines etapes: brancher des donnees open data, geotraitements et scoring avance.
