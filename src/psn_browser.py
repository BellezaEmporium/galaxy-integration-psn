import asyncio
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional
from consts import OAUTH_LOGIN_REDIRECT_URL, OAUTH_LOGIN_URL

from playwright.async_api import async_playwright

if "pkg_resources" not in sys.modules:
    import types

    _pkg = types.ModuleType("pkg_resources")

    def _resource_string(package_name, resource_path):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(plugin_dir, package_name, resource_path)
        with open(full_path, "rb") as f:
            return f.read()

    _pkg_any: Any = _pkg
    _pkg_any.resource_string = _resource_string
    sys.modules["pkg_resources"] = _pkg

DEBUG_PORT = 9222

TARGET_COOKIE_NAMES = {
    "pdccws_p",
    "isSignedIn",
    "pdcsi",
    "pdcws2",
    "PIM-SESSION-ID",
    "sc-cmp-id",
    "session",
    "userinfo",
}

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

async def _accept_cookie_banner(page):
    try:
        locator = page.locator('onetrust-accept-btn-handler').first
        if await locator.is_visible(timeout=2000):
            await locator.click()
            await asyncio.sleep(2)
            return True
    except Exception:
        pass

    return False


def _find_chrome() -> Optional[str]:
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    for pattern in [
        r"C:\Program Files\Google\Chrome\Application\*\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\*\chrome.exe",
    ]:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


async def launch_login_and_get_cookies() -> List[Dict]:
    chrome_path = _find_chrome()
    if not chrome_path:
        raise RuntimeError("Chrome or Edge not found.")

    user_data_dir = tempfile.mkdtemp(prefix="psn_login_")
    chrome_proc = subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={user_data_dir}",
            "--window-size=700,600",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            OAUTH_LOGIN_URL,
        ]
    )

    await asyncio.sleep(3)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()

            for _ in range(300):
                current_url = page.url or ""
                if current_url.startswith(OAUTH_LOGIN_REDIRECT_URL):
                    await asyncio.sleep(2)
                    await _accept_cookie_banner(page)
                    await asyncio.sleep(2)
                    cookies = await context.cookies()
                    for url in (
                        "https://www.playstation.com/",
                        "https://io.playstation.com/",
                        "https://web.np.playstation.com/",
                    ):
                        try:
                            await page.goto(url, wait_until="networkidle", timeout=15000)
                            await asyncio.sleep(1)
                        except Exception:
                            pass

                    cookies = await context.cookies()
                    selected = []

                    for cookie in cookies:
                        name = cookie.get("name")
                        if name not in TARGET_COOKIE_NAMES:
                            continue
                        if name == "isSignedIn" and str(cookie.get("value", "")).lower() != "true":
                            continue

                        selected.append(
                            {
                                "name": name,
                                "value": cookie.get("value", ""),
                                "domain": cookie.get("domain", ""),
                                "path": cookie.get("path", "/"),
                                "secure": cookie.get("secure", False),
                                "httpOnly": cookie.get("httpOnly", False),
                                "expires": cookie.get("expires", -1),
                            }
                        )

                    await browser.close()
                    return selected

                await asyncio.sleep(1)

            raise TimeoutError("Login timed out after 5 minutes")
    finally:
        chrome_proc.terminate()
        shutil.rmtree(user_data_dir, ignore_errors=True)