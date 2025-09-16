from fastapi import FastAPI
from .database import Base, engine
from .routers import entries, balance, piece, imports, checks, accounts, journals, clients, exercices, history, controls, fec, chart

app = FastAPI(title="Compta MVP")

# Créer les tables
def init_db():
    Base.metadata.create_all(bind=engine)

init_db()

# Routers
app.include_router(entries.router)
app.include_router(balance.router)
app.include_router(piece.router)
app.include_router(imports.router)
app.include_router(checks.router)
app.include_router(accounts.router)
app.include_router(journals.router)
app.include_router(clients.router)
app.include_router(exercices.router)
app.include_router(history.router)
app.include_router(controls.router)
app.include_router(fec.router)
app.include_router(chart.router)


@app.get("/")
def root():
    return {"ok": True}
