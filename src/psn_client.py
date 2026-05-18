import asyncio
import logging
import random
from datetime import datetime, timezone
from functools import partial
from typing import List, NewType
from asyncio import Semaphore
from consts import PLAYED_GAME_LIST_URL, GAME_LIST_URL, USER_INFO_URL

from galaxy.api.errors import UnknownBackendResponse
from galaxy.api.types import SubscriptionGame
from parsers import PSNGamesParser

DEFAULT_LIMIT = random.randint(25, 50)
PLAYED_GAME_LIST_URL = PLAYED_GAME_LIST_URL.format(size=DEFAULT_LIMIT)
UnixTimestamp = NewType("UnixTimestamp", int)


def parse_timestamp(earned_date) -> UnixTimestamp:
    date_format = "%Y-%m-%dT%H:%M:%S.%fZ" if '.' in earned_date else "%Y-%m-%dT%H:%M:%SZ"
    dt = datetime.strptime(earned_date, date_format)
    dt = datetime.combine(dt.date(), dt.time(), timezone.utc)
    return UnixTimestamp(int(dt.timestamp()))

class PSNClient:
    def __init__(self, http_client):
        self._http_client = http_client
        self._cache = {}
        self._semaphore = Semaphore(2)
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apollographql-client-name": "oracle-web-toolbar",
            "apollographql-client-version": "1.14.0",
            "x-psn-store-locale-override": "en-US"
        }

    @staticmethod
    async def _async(method, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(method, *args, **kwargs))

    async def _fetch_url(self, url, *args, **kwargs):
        async with self._semaphore:
            if url in self._cache:
                return self._cache[url]
                
            await asyncio.sleep(random.uniform(1.5, 3.5))
            
            response = await self._http_client.get(url, headers=self._headers, *args, **kwargs)
            self._cache[url] = response
            return response

    async def fetch_paginated_data(
        self,
        parser,
        url,
        operation_name,
        counter_name,
        limit=None,
        *args,
        **kwargs
    ):
        if limit is None:
            limit = random.randint(25, 50)
            
        first_url = url.format(size=limit, start=0)
        response = await self._fetch_url(first_url, *args, **kwargs)
        if not response:
            return []
            
        try:
            total = int(response["data"][operation_name]["pageInfo"].get(counter_name, 0))
        except (ValueError, KeyError, TypeError) as e:
            raise UnknownBackendResponse(str(e))
            
        responses = [response]
        
        if total > limit:
            tasks = []
            offset = limit
            
            while offset < total:
                page_size = random.randint(25, 50)
                tasks.append(self._fetch_url(url.format(size=page_size, start=offset), *args, **kwargs))
                offset += page_size
                
            for task in tasks:
                responses.append(await task)
                if random.random() < 0.7:
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    
        try:
            return [item for res in responses for item in parser(res)]
        except Exception:
            logging.exception("Cannot parse data")
            raise UnknownBackendResponse()

    async def fetch_data(self, parser, *args, **kwargs):
        response = await self._http_client.get(*args, headers=self._headers, **kwargs)
        try:
            return parser(response)
        except Exception:
            logging.exception("Cannot parse data")
            raise UnknownBackendResponse()

    async def async_get_own_user_info(self):
        def user_info_parser(response):
            logging.debug(f'user profile data: {response}')
            try:
                return response["data"]["oracleUserProfileRetrieve"]["accountId"], \
                       response["data"]["oracleUserProfileRetrieve"]["onlineId"]
            except (KeyError, TypeError) as e:
                raise UnknownBackendResponse(str(e))
        return await self.fetch_data(user_info_parser, USER_INFO_URL)

    async def get_psplus_status(self) -> bool:
        def user_subscription_parser(response):
            try:
                status = response["data"]["oracleUserProfileRetrieve"]['isPsPlusMember']
                if status in [0, 1, True, False]:
                    return bool(status)
                raise TypeError
            except (KeyError, TypeError) as e:
                raise UnknownBackendResponse(str(e))
        return await self.fetch_data(user_subscription_parser, USER_INFO_URL)

    async def get_subscription_games(self) -> List[SubscriptionGame]:
        parser = PSNGamesParser(self._http_client)
        return await parser.parse()

    async def async_get_purchased_games(self):
        def games_parser(response):
            try:
                games = response['data']['purchasedTitlesRetrieve']['games']
                return [
                    {"titleId": title["titleId"], "name": title["name"]} for title in games
                ] if games else []
            except (KeyError, TypeError) as e:
                raise UnknownBackendResponse(str(e))
        return await self.fetch_paginated_data(games_parser, GAME_LIST_URL, "purchasedTitlesRetrieve", "totalCount")

    async def async_get_played_games(self):
        def games_parser(response):
            try:
                games = response['data']['gameLibraryTitlesRetrieve']['games']
                return [
                    {"titleId": title["titleId"], "name": title["name"], "lastPlayedDateTime": title["lastPlayedDateTime"]} for title in games
                ] if games else []
            except (KeyError, TypeError) as e:
                raise UnknownBackendResponse(str(e))
        return await self.fetch_data(games_parser, PLAYED_GAME_LIST_URL)
