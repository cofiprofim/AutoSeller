# Wanted to add this but too complicated

# class TasksManager:
#     success_emoji = "✅"
#     error_emoji = "❌"
#     skip_emoji = "⚫️"

#     def __init__(
#         self,
#         char_limit: Optional[int] = 4096,
#         success_emoji: Optional[str] = None,
#         error_emoji: Optional[str] = None
#     ) -> None:
#         self.char_limit = char_limit
#         self._tasks = ""

#         if success_emoji is not None:
#             self.success_emoji = success_emoji
#         if error_emoji is not None:
#             self.error_emoji = error_emoji

#     def check_tasks(func: callable):
#         def wrapper(self, *args, **kwargs):
#             if len(self.tasks) >= self.char_limit:
#                 self.tasks = ""

#             func(self, *args, **kwargs)
#         return wrapper

#     @check_tasks
#     def add_new(self, text: str, emoji_type: Literal["success", "error", "skip"]) -> None:
#         if emoji_type == "success":
#             self._tasks = self._tasks + f"{self.success_emoji} {text}\n"
#         elif emoji_type == "error":
#             self._tasks = self._tasks + f"{self.error_emoji} {text}\n"
#         elif emoji_type == "skip":
#             self._tasks = self._tasks + f"{self.skip_emoji} {text}\n"

#     @check_tasks
#     def add_success(self, text: str) -> None:
#         self._tasks = self._tasks + f"{self.success_emoji} {text}\n"

#     @check_tasks
#     def add_error(self, text: str) -> None:
#         self._tasks = self._tasks + f"{self.error_emoji} {text}\n"

#     @check_tasks
#     def add_skip(self, text: str) -> None:
#         self._tasks = self._tasks + f"{self.skip_emoji} {text}\n"

#     @property
#     def tasks(self) -> str:
#         return self._tasks

#     @classmethod
#     def set_success(cls, new: str) -> None:
#         cls.success_emoji = new

#     @classmethod
#     def set_error(cls, new: str) -> None:
#         cls.error_emoji = new

#     @classmethod
#     def set_skip(cls, new: str) -> None:
#         cls.skip_emoji = new

#     def __len__(self) -> int:
#         return len(self._tasks)

#     def __str__(self) -> str:
#         return self._tasks.strip()

#     __repr__ = __str__
