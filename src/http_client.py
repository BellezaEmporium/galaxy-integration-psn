import asyncio
import logging
import random
import time
from http.cookies import SimpleCookie
from typing import Dict
from consts import WEB_NP_URL, REFRESH_COOKIES_URL

import aiohttp
from galaxy.api.errors import UnknownBackendResponse
from galaxy.http import create_client_session, handle_exception
from yarl import URL


class CookieJar(aiohttp.CookieJar):
    def __init__(self):
        super().__init__()
        self._cookies_updated_callback = None

    def set_cookies_updated_callback(self, callback):
        self._cookies_updated_callback = callback

    def update_cookies(self, cookies, *args, **kwargs):
        super().update_cookies(cookies, *args, **kwargs)
        if cookies and self._cookies_updated_callback:
            self._cookies_updated_callback(list(self))


class HttpClient:
    def __init__(self):
        self._cookie_jar = CookieJar()
        self._session = create_client_session(cookie_jar=self._cookie_jar)
        self._last_request_time = 0.0
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        ]
        self._current_user_agent = random.choice(self._user_agents)

    def _get_realistic_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self._current_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    async def _add_delay(self):
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < 1.0:
            delay = 1.0 - time_since_last_request + random.uniform(0.5, 2.0)
            await asyncio.sleep(delay)

        self._last_request_time = time.time()

        if random.random() < 0.1:
            self._current_user_agent = random.choice(self._user_agents)

    async def close(self):
        await self._session.close()

    def clear_cookies(self):
        self._cookie_jar.clear()

    def set_cookies_updated_callback(self, callback):
        self._cookie_jar.set_cookies_updated_callback(callback)

    def update_cookies(self, cookies):
        self._cookie_jar.update_cookies(cookies)

    def update_cookies_from_browser(self, cookies):
        for cookie in cookies:
            name = cookie.get("name")
            value = cookie.get("value", "")
            domain = cookie.get("domain") or ""
            path = cookie.get("path") or "/"

            if not name:
                continue

            host = domain.lstrip(".") or "www.playstation.com"
            if not path.startswith("/"):
                path = "/" + path

            response_url = URL.build(scheme="https", host=host, path=path)

            simple_cookie = SimpleCookie()
            simple_cookie[name] = value
            simple_cookie[name]["domain"] = domain or host
            simple_cookie[name]["path"] = path

            self._cookie_jar.update_cookies(simple_cookie, response_url=response_url)

    async def warm_up_playstation_session(self):
        for url in (
            "https://www.playstation.com/",
            "https://io.playstation.com/",
            WEB_NP_URL,
        ):
            try:
                await self.get(url, silent=True, get_json=False)
            except Exception:
                pass

    async def _request(self, method, url, *args, **kwargs):
        await self._add_delay()

        headers = kwargs.get("headers", {})
        realistic_headers = self._get_realistic_headers()
        realistic_headers.update(headers)
        kwargs["headers"] = realistic_headers

        with handle_exception():
            return await self._session.request(method, url, *args, **kwargs)

    async def get_response(self, url, *args, **kwargs):
        return await self._request("GET", url, *args, **kwargs)

    async def get(self, url, *args, **kwargs):
        silent = kwargs.pop("silent", False)
        get_json = kwargs.pop("get_json", True)
        response = await self._request("GET", url, *args, **kwargs)
        try:
            raw_response = "***" if silent else await response.text()
            logging.debug(f"Response for:\n{url}\n{raw_response}")
            return await response.json() if get_json else raw_response
        except ValueError:
            logging.exception(f"Invalid response data for:\n{url}")
            raise UnknownBackendResponse()

    async def post(self, url, *args, **kwargs):
        logging.debug(f"Sending data:\n{url}")
        response = await self._request("POST", url, *args, **kwargs)
        response_text = await response.text()
        logging.debug(f"Response for post:\n{url}\n{response_text}")
        return response

    async def refresh_cookies(self):
        await self.get(REFRESH_COOKIES_URL, silent=True, get_json=False)