from __future__ import annotations

import json
from pathlib import Path


class Translator:
    _inst: Translator | None = None

    def __init__(self, language: str) -> None:
        self._language = language
        self._strings: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        path = Path(__file__).parent / f"{self._language}.json"
        if path.exists():
            self._strings = json.loads(path.read_text(encoding="utf-8"))

    @property
    def language(self) -> str:
        return self._language

    def get(self, key: str) -> str:
        return self._strings.get(key, key)

    @classmethod
    def setup(cls, language: str) -> None:
        cls._inst = cls(language)

    @classmethod
    def instance(cls) -> Translator:
        if cls._inst is None:
            cls._inst = cls("zh")
        return cls._inst

    @classmethod
    def translate(cls, key: str) -> str:
        return cls.instance().get(key)


def _(key: str) -> str:
    return Translator.translate(key)
