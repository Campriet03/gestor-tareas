"""Crea las tablas en la base configurada: python -m app.init_db"""
from .config import database_url, load_env
from .db import make_database


def main():
    load_env()
    db = make_database(database_url())
    db.init_schema()
    print("Esquema aplicado correctamente.")


if __name__ == "__main__":
    main()
