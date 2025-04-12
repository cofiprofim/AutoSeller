import asyncio
from os.path import basename
import json

from typing import Union, Any, Iterable, Optional, Literal

from .visuals import Display
from .constants import WEBHOOK_PATTERN
from .clients import ClientSession


class IgnoreNew:
    def __set_name__(self, _, name: str) -> None:
        self.name = f"_{name}"

    def __get__(self, instance, _):
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        if getattr(instance, self.name, None):
            return None

        setattr(instance, self.name, value)


class WithBool:
    def __init__(self) -> None:
        self.__bool = False

    def __enter__(self):
        self.__bool = True

    def __exit__(self, *_):
        self.__bool = False

    def __bool__(self) -> bool:
        return self.__bool

    def __repr__(self) -> str:
        return str(self.__bool)


class AssetsLoader:
    def __init__(self, func: callable, source: Iterable, batch_amount: Optional[int] = None):
        self.wrapped = func
        self.source = source
        self.batch_amount = (batch_amount or 0)

    async def load(self, *func_args, **func_kwargs):
        tasks = [
            asyncio.create_task(self.wrapped(s, *func_args, **func_kwargs))
            for s in slice_list(self.source, self.batch_amount)
        ]
        return sum(await asyncio.gather(*tasks), [])


class FileSync(set):
    def __init__(self, filename: str) -> None:
        self.filename = filename

        items = load_file(filename)
        if not isinstance(items, list):
            Display.exception("Invalid format type provided")

        super().__init__(items)

    def __getattribute__(self, name: str) -> Union[Any, callable]:
        attr = super().__getattribute__(name)

        if (
            attr is not None
            and not name.startswith("_")
            and callable(attr)
        ):
            def wrapper(*args, **kwargs):
                attr(*args, **kwargs)

                with open(self.filename, "w") as f:
                    # noinspection PyTypeChecker
                    json.dump(list(self), f)

            return wrapper
        return attr


def slice_list(iterable: Iterable[Any], n: int) -> Iterable[Iterable[Any]]:
    if not n:
        return iterable

    # noinspection PyTypeChecker
    return [iterable[i:i + n] for i in range(0, len(iterable), n)]


def define_status(flag: bool) -> str:
    return "Enabled" if flag else "Disabled"


def load_file(file_path: str) -> dict:
    try:
        return json.load(open(file_path, "r"))

    except json.JSONDecodeError:
        file_name = basename(file_path)
        return Display.exception(f"Failed to decode \"{file_name}\"")

    except FileNotFoundError:
        file_name = basename(file_path)
        return Display.exception(f"File \"{file_name}\" was not found")

    except Exception as err:
        file_name = basename(file_path)
        return Display.exception(f"Failed to load \"{file_name}\" file: {err}")


def define_sale_price(undercut_amount: int, undercut_type: Literal["amount", "percent"],
                      limit_price: int, lowest_price: int) -> int:
    def min_sale(price: int) -> int:
        profit = price // 2

        while (price // 2) >= profit:
            price -= 1

        return price + 1

    if undercut_type == "amount":
        final_price = lowest_price - undercut_amount
    else:
        final_price = round(lowest_price - (lowest_price / 100 * undercut_amount))

    final_price = min_sale(final_price)
    return final_price if final_price > limit_price else limit_price


async def is_webhook_exists(webhook_url: str) -> bool:
    if not WEBHOOK_PATTERN.match(webhook_url):
        return False

    async with ClientSession() as session:
        async with session.get(webhook_url) as response:
            return True if (await response.json()).get("name") is not None else False


async def check_for_update(code_url: str, _version: str) -> bool:
    async with ClientSession() as session:
        async with session.get(code_url) as response:
            try:
                version = (await response.text()).strip().split("VERSION = \"")[1].split("\"")[0]
            except IndexError:
                return False

            return True if version != _version else False
