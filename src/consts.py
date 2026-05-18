OAUTH_LOGIN_REDIRECT_URL = "https://www.playstation.com/"
OAUTH_LOGIN_URL = (
    f"https://web.np.playstation.com/api/session/v1//signin"
    f"?redirect_uri=https://io.playstation.com/central/auth/login"
    f"?locale=en_US&postSignInURL={OAUTH_LOGIN_REDIRECT_URL}"
    f"&cancelURL={OAUTH_LOGIN_REDIRECT_URL}"
)

REFRESH_COOKIES_URL = OAUTH_LOGIN_URL
WEB_NP_URL = "https://web.np.playstation.com/"
DEFAULT_TIMEOUT = 30


GAME_LIST_URL = "https://web.np.playstation.com/api/graphql/v1/op" \
                "?operationName=getPurchasedGameList" \
                '&variables={{"isActive":true,"platform":["ps3","ps4","ps5"],"start":{start},"size":{size},"sortBy":"ACTIVE_DATE","sortDirection":"desc"}}' \
                '&extensions={{"persistedQuery":{{"version":1,"sha256Hash":"827a423f6a8ddca4107ac01395af2ec0eafd8396fc7fa204aaf9b7ed2eefa168"}}}}'

PLAYED_GAME_LIST_URL = "https://web.np.playstation.com/api/graphql/v1/op" \
                       "?operationName=getUserGameList" \
                       '&variables={{"categories":"ps3_game,ps4_game,ps5_native_game","limit":{size}}}' \
                       '&extensions={{"persistedQuery":{{"version":1,"sha256Hash":"e0136f81d7d1fb6be58238c574e9a46e1c0cc2f7f6977a08a5a46f224523a004"}}}}'

USER_INFO_URL = "https://web.np.playstation.com/api/graphql/v1/op" \
                "?operationName=getProfileOracle" \
                "&variables={}" \
                '&extensions={"persistedQuery":{"version":1,"sha256Hash":"fc0d765f537f3dce3e0d91c71e85daa401042ba43066acde9f8f584faced10df"}}'

PSN_PLUS_SUBSCRIPTIONS_URL = 'https://store.playstation.com/subscriptions'