import asyncio
import aiohttp
import inspect
import re

from typing import Optional

from .visuals import Display

__all__ = ("ClientSession", "Auth")


class ClientSession(aiohttp.ClientSession):
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        # noinspection PyTypeChecker
        kwargs.update({
            "connector": aiohttp.TCPConnector(limit=None, ssl=False),
            "trust_env": True,
        })

        super().__init__(base_url, **kwargs)

    def _request(self, method: str, url: str, **kwargs):
        kwargs.update({"ssl": False})

        if re.match(r"\Ahttps?://", url) is None:
            url = "https://" + url

        return super()._request(method, url, **kwargs)


class Auth(ClientSession):
    __slots__ = ("cookie", "user_id", "name", "username", "has_premium")

    def __init__(self, cookie: str) -> None:
        super().__init__(cookies={".ROBLOSECURITY": cookie})

        self.cookie = cookie

        self.user_id = None
        self.name = None
        self.username = None
        self.has_premium = None

    async def close_session(self):
        await self.close()

    async def fetch_csrf_token(self, csrf_token: Optional[str] = None) -> None:
        if csrf_token is None:
            self.headers.pop("x-csrf-token", None)

            async with self.post("auth.roblox.com/v1/login") as response:
                csrf_token = response.headers.get("x-csrf-token")

                if csrf_token is None:
                    Display.exception("Failed to get csrf token")

        self.headers.update({"x-csrf-token": csrf_token})

    async def fetch_user_info(self) -> Optional[int]:
        async with self.get("users.roblox.com/v1/users/authenticated") as response:
            data = await response.json()

            if (
                response.status != 200
                or data.get("errors")
                and not data["errors"][0].get("code")
            ):
                return None

            self.user_id = data.get("id")
            self.name = data.get("displayName")
            self.username = data.get("name")

            return self.user_id

    async def fetch_premium(self) -> Optional[bool]:
        if self.user_id is None and await self.fetch_user_info() is None:
            return None

        async with self.get(f"premiumfeatures.roblox.com/v1/users/{self.user_id}/validate-membership") as response:
            self.has_premium = await response.json()
            return self.has_premium

    async def csrf_token_updater(self, interval: int = 30) -> None:
        while True:
            await self.fetch_csrf_token()
            await asyncio.sleep(interval)

    @classmethod
    def has_auth(cls, func: Optional[callable] = None, /, *, attr_name: str = "auth"):
        def decorator(wrapped: callable):
            async def async_wrapper(instance, *args, **kwargs):
                attr = getattr(instance, attr_name, None)

                if not isinstance(attr, cls):
                    return None

                await wrapped(instance, *args, **kwargs)

            def wrapper(instance, *args, **kwargs):
                attr = getattr(instance, attr_name, None)
                print(attr)

                if not isinstance(attr, cls):
                    return None

                wrapped(instance, *args, **kwargs)

            return async_wrapper if inspect.iscoroutinefunction(wrapped) else wrapper

        if func is None:
            return decorator

        return decorator(func)
