import logging
from typing import List, Dict, Any
import random

from galaxy.api.errors import UnknownBackendResponse
from galaxy.api.types import SubscriptionGame

logger = logging.getLogger(__name__)

BASIC_LIST_PSPLUS = "https://www.playstation.com/bin/imagic/gameslist?locale=en-us&categoryList=plus-games-list"
BASIC_LIST_UBI = "https://www.playstation.com/bin/imagic/gameslist?locale=en-us&categoryList=ubisoft-classics-list"
BASIC_LIST_PSPLUS_CLASSICS = "https://www.playstation.com/bin/imagic/gameslist?locale=en-us&categoryList=plus-classics-list"
BASIC_LIST_PSPLUS_MONTHLY = "https://www.playstation.com/bin/imagic/gameslist?locale=en-us&categoryList=plus-monthly-games-list"

class PSNGamesParser:
    def __init__(self, http_client=None):
        self._http_client = http_client
        
    async def parse(self) -> List[SubscriptionGame]:
        results: List[SubscriptionGame] = []
        urls = [BASIC_LIST_PSPLUS, BASIC_LIST_UBI, BASIC_LIST_PSPLUS_CLASSICS, BASIC_LIST_PSPLUS_MONTHLY]
        random.shuffle(urls)
        
        for url in urls:
            try:
                if self._http_client:
                    response = await self._http_client.get(url, get_json=True)
                    data: Dict[str, Any] = response
                else:
                    import requests
                    response = requests.get(url)
                    response.raise_for_status()
                    data: Dict[str, Any] = response.json()
                    
                catalogs: List[Dict[str, Any]] = data.get("gamesList", [])
                for catalog in catalogs:
                    games: List[Dict[str, Any]] = catalog.get("games", [])
                    for game in games:
                        cid = game.get("conceptId")
                        name = game.get("name")
                        if cid and name:
                            results.append(SubscriptionGame(game_id=str(cid), game_title=name))
            except Exception as e:
                logger.error(f"Error fetching from {url}: {e}")
                raise UnknownBackendResponse()
                
        return results
