"""Module racine (équivalent de l'AppModule Nest) : la liste des modules de l'API.

Pour ajouter un module : créer app/modules/<nom>/ avec controller.py, service.py, dto.py,
exporter `router` dans son __init__.py, puis l'ajouter ci-dessous.
"""

from fastapi import FastAPI

from app.modules import geodata

MODULES = [geodata]


def register_modules(app: FastAPI) -> None:
    for module in MODULES:
        app.include_router(module.router)
