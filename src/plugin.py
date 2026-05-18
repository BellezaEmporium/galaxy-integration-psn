import logging
import sys
from typing import Any, AsyncGenerator, List

from galaxy.api.consts import LicenseType, Platform
from galaxy.api.errors import InvalidCredentials
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.types import (
    Authentication,
    Game,
    GameTime,
    LicenseInfo,
    NextStep,
    Subscription,
    SubscriptionGame,
)

from consts import OAUTH_LOGIN_REDIRECT_URL, OAUTH_LOGIN_URL
from http_client import HttpClient
from psn_browser import launch_login_and_get_cookies
from psn_client import PSNClient, parse_timestamp
from version import __version__

AUTH_PARAMS = {
    "window_title": "Login to PlayStation Network",
    "window_width": 536,
    "window_height": 675,
    "start_uri": OAUTH_LOGIN_URL,
    "end_uri_regex": "^" + OAUTH_LOGIN_REDIRECT_URL + ".*",
}

logger = logging.getLogger(__name__)


class PSNPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(Platform.Psn, __version__, reader, writer, token)
        self._http_client = HttpClient()
        self._psn_client = PSNClient(self._http_client)
        logging.getLogger("urllib3").setLevel(logging.FATAL)

    async def _authenticate_from_browser_cookies(self, browser_cookies):
        if not browser_cookies:
            raise InvalidCredentials()

        self._http_client.set_cookies_updated_callback(None)
        self._http_client.clear_cookies()
        self._http_client.update_cookies_from_browser(browser_cookies)
        await self._http_client.warm_up_playstation_session()

        user_id, user_name = await self._psn_client.async_get_own_user_info()
        if not user_id:
            raise InvalidCredentials()

        return Authentication(user_id=user_id, user_name=user_name)

    async def _authenticate_with_browser(self):
        try:
            browser_cookies = await launch_login_and_get_cookies()
        except Exception as e:
            logger.warning(f"Browser auth failed: {e}")
            return NextStep("web_session", AUTH_PARAMS)

        if not browser_cookies:
            return NextStep("web_session", AUTH_PARAMS)

        self._store_browser_cookies(browser_cookies)
        return await self._authenticate_from_browser_cookies(browser_cookies)

    async def authenticate(self, stored_credentials=None):
        browser_cookies = (stored_credentials or {}).get("browser_cookies")

        if browser_cookies:
            try:
                return await self._authenticate_from_browser_cookies(browser_cookies)
            except InvalidCredentials:
                logger.warning("Stored browser cookies are invalid, opening browser login")

        return await self._authenticate_with_browser()

    async def pass_login_credentials(self, step, credentials, cookies):
        browser_cookies = [
            {
                "name": cookie.get("name"),
                "value": cookie.get("value", ""),
                "domain": cookie.get("domain", ""),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", False),
                "httpOnly": cookie.get("httpOnly", False),
                "expires": cookie.get("expires", -1),
            }
            for cookie in cookies
            if cookie.get("name")
        ]

        self._store_browser_cookies(browser_cookies)
        return await self._authenticate_from_browser_cookies(browser_cookies)

    def _store_browser_cookies(self, browser_cookies):
        self.store_credentials({"browser_cookies": browser_cookies})

    async def get_subscriptions(self) -> List[Subscription]:
        is_plus_active = await self._psn_client.get_psplus_status()
        return [Subscription(subscription_name="PlayStation PLUS", end_time=None, owned=is_plus_active)]

    async def get_subscription_games(
        self, subscription_name: str, context: Any
    ) -> AsyncGenerator[List[SubscriptionGame], None]:
        yield await self._psn_client.get_subscription_games()

    async def prepare_game_times_context(self, game_ids: List[str]) -> Any:
        return {game["titleId"]: game for game in await self._psn_client.async_get_played_games()}

    async def get_game_time(self, game_id: str, context: Any) -> GameTime:
        time_played, last_played_game = None, None
        game = context.get(game_id)
        if game:
            last_played_game = parse_timestamp(game.get("lastPlayedDateTime"))
        return GameTime(game_id, time_played, last_played_game)

    async def get_owned_games(self):
        def game_parser(title):
            return Game(
                game_id=title["titleId"],
                game_title=title["name"],
                dlcs=[],
                license_info=LicenseInfo(LicenseType.SinglePurchase, None),
            )

        purchased_games = await self._psn_client.async_get_purchased_games()
        played_games_raw = await self._psn_client.async_get_played_games()
        played_games = [{"titleId": title["titleId"], "name": title["name"]} for title in played_games_raw]
        unique_all_games = {game["titleId"]: game for game in played_games + purchased_games}.values()
        return [game_parser(game) for game in unique_all_games]

    async def shutdown(self):
        await self._http_client.close()


def main():
    create_and_run_plugin(PSNPlugin, sys.argv)


if __name__ == "__main__":
    main()