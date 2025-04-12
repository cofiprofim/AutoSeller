from rgbprint import Color, rgbprint
from datetime import datetime
import aioconsole
import functools
import os
import re
import shutil

from typing import (
    Optional,
    NoReturn,
    Mapping,
    List,
    Union
)

from .constants import COLOR_CODE_PATTERN, TITLE, SIGNATURE

__all__ = ("Tools", "BaseColors", "Display")


class Tools:
    @staticmethod
    def exit_program(error_code: Optional[int] = None) -> NoReturn:
        os.system("pause" if os.name == "nt" else "read -p \"Press any key to continue . . .\"")
        os._exit(error_code or 0)

    @staticmethod
    def clear_console() -> None:
        os.system("cls" if os.name == "nt" else "clear")


class BaseColors:
    main = Color(205, 0, 236)
    accent = Color(112, 102, 114)
    timestamp = Color(190, 190, 190)
    info = Color(127, 127, 127)
    success = Color(0, 255, 0)
    skipping = Color(110, 110, 110)
    error = Color(255, 0, 0)
    gray = Color(168, 168, 168)
    reset = Color.reset


class Display(BaseColors):
    @staticmethod
    def _print_centered(text: str, color: Optional[Color] = None, end: str = "\n") -> None:
        def _get_terminal_size() -> int:
            return shutil.get_terminal_size().columns

        def _remove_color_codes(text: str) -> str:
            return re.sub(COLOR_CODE_PATTERN, "", text)

        terminal_size = _get_terminal_size()

        for line in text.splitlines():
            indent = (terminal_size - len(_remove_color_codes(line))) // 2
            rgbprint((" " * indent) + line, color=color, end=end)

    @staticmethod
    def _make_display(color: Color, *,
                      end: str = "\n", tag: Optional[str] = None):

        def decorator(func: callable) -> classmethod:
            final_tag = (tag or func.__name__).upper()

            @functools.wraps(func)
            def wrapper(cls, text: str):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                final_text = re.sub(r"\[g(.*)]",
                                    rf"{BaseColors.gray}\g<1>{BaseColors.reset}",
                                    text)

                print(f"{super().timestamp}{timestamp}"
                      f" > {color}{final_tag}{super().reset}"
                      f" | {final_text}", end=end)

                func(cls, text)

            return classmethod(wrapper)
        return decorator

    @classmethod
    def main(cls) -> None:
        cls._print_centered(TITLE, super().main)
        cls._print_centered(SIGNATURE, super().accent, end="\n\n")

    @_make_display(BaseColors.info)
    def info(cls, text: str): ...

    @_make_display(BaseColors.success)
    def success(cls, text: str): ...

    @_make_display(BaseColors.error)
    def exception(cls, _: str):
        Tools.exit_program()

    @_make_display(BaseColors.error)
    def error(cls, text: str): ...

    @_make_display(BaseColors.skipping)
    def skipping(cls, text: str): ...

    @classmethod
    async def input(cls, text: str) -> str:
        return await cls.custom(text, "input", super().gray, use_input=True)

    @classmethod
    async def custom(cls, text: str, tag: str, color: Color, *,
                     exit_after: bool = False, use_input: bool = False,
                     end: str = "\n") -> Union[str, NoReturn]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        display_text = (f"{super().timestamp}{timestamp}"
                        f" > {color}{tag.upper()}{super().reset}"
                        f" | {text}")

        choice = (await aioconsole.ainput(display_text)).lower().strip() \
            if use_input \
            else await aioconsole.aprint(display_text, end=end)

        if exit_after:
            Tools.exit_program()

        return choice

    @classmethod
    def sections(cls, data: Mapping[str, Mapping[str, str]]) -> None:
        def _define_longest(sections: List[str]) -> int:
            return len(max(sections, key=lambda x: len(str(x))))

        longest_name = 0
        longest_value = 0

        for values in data.values():
            name_length = _define_longest(values.keys())
            if name_length > longest_name:
                longest_name = name_length

            value_length = _define_longest(values.values())
            if value_length > longest_value:
                longest_value = value_length

        for section, values in data.items():
            cls._print_centered(f">{super().gray}>{super().reset} {section} {super().gray}<{super().reset}<",
                                Color.white, "\n\n")

            for name, value in values.items():
                name_indent = " " * (longest_name - len(str(name)))
                value_indent = " " * (longest_value - len(str(value)))

                cls._print_centered(f"{super().gray}> {name}{name_indent} :{super().reset} {value}{value_indent}")

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
    #         cls._print_centered(f">{BaseColor.gray}>{super().reset} {section} {BaseColor.gray}<{super().reset}<", Color.white, "\n\n")

    #         for name, value in values.items():
    #             name_indent = " " * (longest_name - len(str(name)))
    #             value_indent = " " * (longest_value - len(str(value)))

    #             cls._print_centered(f"{BaseColor.gray}[{name}] > {name_indent} :{super().reset} {value}{value_indent}")

    #         print()

    # async def display_loading()
