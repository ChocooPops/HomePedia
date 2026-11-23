from fastapi.responses import HTMLResponse

from app.core.controller import controller, get
from app.modules.leboncoin.service import LeboncoinServiceDep


@controller("/leboncoin", tags=["leboncoin"])
class LeboncoinController:
    service: LeboncoinServiceDep

    @get("/search", response_class=HTMLResponse)
    async def get_search_page(self):
        return await self.service.get_search_page()
