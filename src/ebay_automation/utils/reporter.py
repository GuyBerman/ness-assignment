"""Allure helpers, so pages and flows don't import allure directly."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import allure

from ebay_automation.utils.logger import get_logger

log = get_logger(__name__)


class Reporter:
    @staticmethod
    @contextmanager
    def step(title: str) -> Iterator[None]:
        log.info("STEP: %s", title)
        with allure.step(title):
            yield

    @staticmethod
    def attach_png(path: Path, name: str) -> None:
        allure.attach.file(str(path), name=name, attachment_type=allure.attachment_type.PNG)

    @staticmethod
    def attach_text(body: str, name: str) -> None:
        allure.attach(body, name=name, attachment_type=allure.attachment_type.TEXT)

    @staticmethod
    def attach_html(body: str, name: str) -> None:
        allure.attach(body, name=name, attachment_type=allure.attachment_type.HTML)

    @staticmethod
    def attach_json(data: Any, name: str) -> None:
        allure.attach(
            json.dumps(data, indent=2, default=str, ensure_ascii=False),
            name=name,
            attachment_type=allure.attachment_type.JSON,
        )

    @staticmethod
    def attach_file(path: Path, name: str, extension: str) -> None:
        allure.attach.file(str(path), name=name, extension=extension)
