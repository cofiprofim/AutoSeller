from rgbprint import Color, rgbprint
from datetime import datetime
from aioconsole import ainput
import os
import re
import shutil

from __main__ import VERSION
from typing import Optional, NoReturn, Mapping, Any, List


GRAY_COLOR = Color(168, 168, 168)

MAIN_COLOR = Color(205, 0, 236)
ACCENT_COLOR = Color(112, 102, 114)

SIGNATURE = f"Limiteds Seller Tool v{VERSION}"
TITLE = r"""  ___        _        _____      _ _           
 / _ \      | |      /  ___|    | | |          
/ /_\ \_   _| |_ ___ \ `--.  ___| | | ___ _ __ 
|  _  | | | | __/ _ \ `--. \/ _ \ | |/ _ \ '__|
| | | | |_| | || (_) /\__/ /  __/ | |  __/ |   
\_| |_/\__,_|\__\___/\____/ \___|_|_|\___|_|    

"""


def _print_centered(text: str, color: Optional[Color] = None, end: str = "\n") -> None:

    def _get_terminal_size() -> int:
        return shutil.get_terminal_size().columns

    def _remove_color_codes(text: str) -> str:
        return re.sub(r"\033\[[0-9;]*m", "", text)

    terminal_size = _get_terminal_size()

    for line in text.splitlines():
        indent = (terminal_size - len(_remove_color_codes(line))) // 2
        rgbprint((" " * indent) + line, color=color, end=end)


def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clear_console() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def display_main() -> None:
    _print_centered(TITLE, MAIN_COLOR)
    _print_centered(SIGNATURE, ACCENT_COLOR, end="\n\n")


def display_info(text: str, end: str = "\n") -> None:
    timestamp = get_current_time()
    print(f"{Color(190, 190, 190)}{timestamp} > {Color(127, 127, 127)}INFO{Color.white} | {text}", end=end)


def display_success(text: str, end: str = "\n") -> None:
    timestamp = get_current_time()
    print(f"{Color(190, 190, 190)}{timestamp} > {Color(0, 255, 0)}SUCCESS{Color.white} | {text}", end=end)


async def display_input(text: str) -> None:
    timestamp = get_current_time()
    choice = await ainput(f"{Color(190, 190, 190)}{timestamp} > {Color(168, 168, 168)}INPUT{Color.white} | {text}")
    return choice.lower().strip()


def display_sections(data: Mapping[str, Mapping[str, str]]) -> None:

    def _define_longest(sections: List[str]) -> int:
        return len(max(sections, key=lambda x: len(str(x))))

    longest_name = 0
    longest_value = 0

    for _, values in data.items():
        name_length = _define_longest(values.keys())
        if name_length > longest_name:
            longest_name = name_length

        value_length = _define_longest(values.values())
        if value_length > longest_value:
            longest_value = value_length

    for section, values in data.items():
        _print_centered(f">{GRAY_COLOR}>{Color.white} {section} {GRAY_COLOR}<{Color.white}<", Color.white, "\n\n")

        for name, value in values.items():
            name_indent = " " * (longest_name - len(str(name)))
            value_indent = " " * (longest_value - len(str(value)))

            _print_centered(f"{GRAY_COLOR}> {name}{name_indent} :{Color.white} {value}{value_indent}")

        print()

# def display_options(data: Mapping[str, Mapping[str, str]]) -> None:
#


def display_selling(text: str, end: str = "\n") -> None:
    timestamp = get_current_time()
    print(f"{Color(190, 190, 190)}{timestamp} > {Color(255, 153, 0)}SELLING{Color.white} | {text}", end=end)


def display_done(text: str) -> NoReturn:
    timestamp = get_current_time()
    ainput(f"{Color(190, 190, 190)}{timestamp} > {Color(163, 133, 0)}DONE{Color.white} | {text}")
    os.system("pause" if os.name == "nt" else "read -p \"Press any key to continue . . .\"")
    os._exit(0)


def display_exception(text: str, end: str = "\n") -> NoReturn:
    timestamp = get_current_time()
    print(f"{Color(190, 190, 190)}{timestamp} > {Color(255, 0, 0)}FATAL{Color.white} | {text}", end=end)
    os.system("pause" if os.name == "nt" else "read -p \"Press any key to continue . . .\"")
    os._exit(0)


def display_error(text: str, end: str = "\n") -> None:
    timestamp = get_current_time()
    print(f"{Color(190, 190, 190)}{timestamp} > {Color(255, 0, 0)}ERROR{Color.white} | {text}", end=end)
