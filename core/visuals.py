from rgbprint import Color, rgbprint
from datetime import datetime
from aioconsole import ainput, aprint
import os
import re
import shutil

from __main__ import VERSION
from typing import (
    Optional,
    NoReturn,
    Mapping,
    List,
    Union,
    Callable
)

__all__ = ("Display", "Tools")


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


def _timestamp_wrap(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        func(*args, _timestamp=timestamp, **kwargs)
    
    return wrapper


class Tools:
    def exit_program(error_code: Optional[int] = None) -> NoReturn:
        os.system("pause" if os.name == "nt" else "read -p \"Press any key to continue . . .\"")
        os._exit(error_code or 0)


    def clear_console() -> None:
        os.system("cls" if os.name == "nt" else "clear")


class Display:
    timestamp_color = Color(190, 190, 190)
    info_color = Color(127, 127, 127)
    success_color = Color(0, 255, 0)
    exception_color = Color(255, 0, 0)
    error_color = Color(255, 0, 0)
    skipping_color = Color(110, 110, 110)
    reset_color = Color.reset
    
    def main() -> None:
        _print_centered(TITLE, MAIN_COLOR)
        _print_centered(SIGNATURE, ACCENT_COLOR, end="\n\n")
    
    @classmethod
    @_timestamp_wrap
    def info(cls, text: str, end: str = "\n", *, _timestamp) -> None:
        print(f"{cls.timestamp_color}{_timestamp} > {cls.info_color}INFO{cls.reset_color} | {text}", end=end)


    @classmethod
    @_timestamp_wrap
    def success(cls, text: str, end: str = "\n", *, _timestamp) -> None:
        print(f"{cls.timestamp_color}{_timestamp} > {cls.success_color}SUCCESS{cls.reset_color} | {text}", end=end)


    @classmethod
    @_timestamp_wrap
    def exception(cls, text: str, end: str = "\n", *, _timestamp) -> NoReturn:
        print(f"{cls.timestamp_color}{_timestamp} > {cls.exception_color}FATAL{cls.reset_color} | {text}", end=end)
        Tools.exit_program()
        

    @classmethod
    @_timestamp_wrap
    def error(cls, text: str, end: str = "\n", *, _timestamp) -> None:
        print(f"{cls.timestamp_color}{_timestamp} > {cls.error_color}ERROR{cls.reset_color} | {text}", end=end)


    @classmethod
    @_timestamp_wrap
    def skipping(cls, text: str, end: str = "\n", *, _timestamp) -> None:
        print(f"{cls.timestamp_color}{_timestamp} > {cls.skipping_color}SKIPPING{cls.reset_color} | {text}", end=end)
    
    @classmethod
    async def custom(cls, text: str, tag: str, color: Color, *,
                     exit_after: Optional[bool] = False, use_input: Optional[bool] = False,
                     end: Optional[str] = "\n") -> Union[None, str, NoReturn]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_text = f"{cls.timestamp_color}{timestamp} > {color}{tag.upper()}{cls.reset_color} | {text}"
        
        choice = (await ainput(display_text)).lower().strip() if use_input else await aprint(display_text, end=end)
        
        if exit_after:
            Tools.exit_program()
        
        return choice
    
    @classmethod
    def sections(cls, data: Mapping[str, Mapping[str, str]]) -> None:
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
            _print_centered(f">{GRAY_COLOR}>{cls.reset_color} {section} {GRAY_COLOR}<{cls.reset_color}<", Color.white, "\n\n")

            for name, value in values.items():
                name_indent = " " * (longest_name - len(str(name)))
                value_indent = " " * (longest_value - len(str(value)))

                _print_centered(f"{GRAY_COLOR}> {name}{name_indent} :{cls.reset_color} {value}{value_indent}")

            print()

    # def display_options(data: Mapping[str, Mapping[str, str]]) -> None:
    #     def _define_longest(sections: List[str]) -> int:
    #         return len(max(sections, key=lambda x: len(str(x))))

    #     longest_name = 0
    #     longest_value = 0

    #     for _, values in data.items():
    #         name_length = _define_longest(values.keys())
    #         if name_length > longest_name:
    #             longest_name = name_length

    #         value_length = _define_longest(values.values())
    #         if value_length > longest_value:
    #             longest_value = value_length

    #     for section, values in data.items():
    #         _print_centered(f">{GRAY_COLOR}>{cls.reset_color} {section} {GRAY_COLOR}<{cls.reset_color}<", Color.white, "\n\n")

    #         for name, value in values.items():
    #             name_indent = " " * (longest_name - len(str(name)))
    #             value_indent = " " * (longest_value - len(str(value)))

    #             _print_centered(f"{GRAY_COLOR}[{name}] > {name_indent} :{cls.reset_color} {value}{value_indent}")

    #         print()

    # async def display_loading()
