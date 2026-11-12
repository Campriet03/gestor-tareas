"""Datos de ejemplo para la demo: python -m app.seed"""
from datetime import date, timedelta

from .config import database_url, load_env
from .db import make_database
from .errors import Conflict
from .services import Services

PASSWORD = "demo-1234"


def main():
    load_env()
    db = make_database(database_url())
    svc = Services(db, "seed", 60)
    try:
        ana = svc.register({"name": "Ana Demo", "email": "ana@demo.com", "password": PASSWORD})
        luis = svc.register({"name": "Luis Demo", "email": "luis@demo.com", "password": PASSWORD})
    except Conflict:
        print("Los datos de ejemplo ya existen.")
        return
    team = svc.create_team(ana["user"]["id"], {"name": "Equipo Demo"})
    svc.invite(ana["user"]["id"], team["id"], {"email": "luis@demo.com"})
    svc.respond_invitation(luis["user"]["id"], svc.my_invitations(luis["user"]["id"])[0]["id"], True)
    project = svc.create_project(ana["user"]["id"], team["id"], {"name": "Sitio web", "description": "Rediseño"})
    today = date.today()
    for title, status, who, days in (("Definir alcance", "done", ana, -5), ("Diseñar portada", "doing", luis, 2),
                                     ("Escribir textos", "todo", luis, 5), ("Publicar", "todo", None, 10)):
        svc.create_task(ana["user"]["id"], project["id"], {
            "title": title, "status": status, "assignee_id": who["user"]["id"] if who else None,
            "due_date": (today + timedelta(days=days)).isoformat()})
    print(f"Listo. Usuarios: ana@demo.com y luis@demo.com (contraseña: {PASSWORD})")


if __name__ == "__main__":
    main()
