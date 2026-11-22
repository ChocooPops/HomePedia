"""Controllers sous forme de classe, à la manière de Nest.js.

    @controller("/geodata", tags=["geodata"])
    class GeoDataController:
        service: GeoDataServiceDep            # injecté à chaque requête

        @get("/regions", response_model=list[RegionDto])
        async def get_regions(self):
            return await self.service.get_regions()

Chaque attribut annoté de la classe est une dépendance FastAPI : à chaque requête,
FastAPI instancie le controller avec ces dépendances, puis appelle la méthode.
Le router généré est exposé dans `GeoDataController.router`.
"""

import functools
import inspect
from typing import Annotated, Any, Callable, get_type_hints

from fastapi import APIRouter, Depends

_ROUTE_ATTR = "__controller_route__"


def _route(method: str) -> Callable[..., Callable]:
    def decorator_factory(path: str = "", **options: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            setattr(func, _ROUTE_ATTR, (method, path, options))
            return func

        return decorator

    return decorator_factory


get = _route("GET")
post = _route("POST")
put = _route("PUT")
patch = _route("PATCH")
delete = _route("DELETE")


def controller(prefix: str = "", **router_options: Any) -> Callable[[type], type]:
    def decorator(cls: type) -> type:
        _make_injectable(cls)
        router = APIRouter(prefix=prefix, **router_options)
        for name, func in list(cls.__dict__.items()):
            route = getattr(func, _ROUTE_ATTR, None)
            if route:
                method, path, options = route
                router.add_api_route(path, _bind(cls, func), methods=[method], name=name, **options)
        cls.router = router
        return cls

    return decorator


def _make_injectable(cls: type) -> None:
    """Le constructeur reçoit les attributs annotés comme dépendances (résolues par FastAPI)."""
    hints = get_type_hints(cls, include_extras=True)
    params = [inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=hint) for name, hint in hints.items()]

    def __init__(self, **dependencies: Any) -> None:
        for name, value in dependencies.items():
            setattr(self, name, value)

    cls.__init__ = __init__
    cls.__signature__ = inspect.Signature(params)


def _bind(cls: type, func: Callable) -> Callable:
    """Remplace `self` par une dépendance qui instancie le controller."""
    signature = inspect.signature(func, eval_str=True)
    self_param, *params = signature.parameters.values()
    self_param = self_param.replace(annotation=Annotated[cls, Depends(cls)], kind=inspect.Parameter.KEYWORD_ONLY)

    @functools.wraps(func)
    async def endpoint(*args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)

    endpoint.__signature__ = signature.replace(
        parameters=[self_param, *(p.replace(kind=inspect.Parameter.KEYWORD_ONLY) for p in params)]
    )
    return endpoint
