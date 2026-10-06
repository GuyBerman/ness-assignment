"""Settings from config/default.yaml, overridden by config/profiles/<ENV>.yaml,
then by EBAY_* environment variables (nested keys use "__", e.g. EBAY_BROWSER__HEADLESS).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"


class BrowserSettings(BaseModel):
    headless: bool = False  # eBay blocks headless browsers
    channel: str | None = "chrome"
    slow_mo: int = 0
    min_navigation_interval_ms: int = 2_000  # minimum gap between page loads
    locale: str = "en-US"
    timeout_ms: int = 15_000
    navigation_timeout_ms: int = 30_000
    viewport_width: int = 1440
    viewport_height: int = 900


class AuthSettings(BaseModel):
    mode: Literal["guest", "storage_state", "credentials"] = "guest"
    storage_state_path: Path = Path("auth/storage_state.json")  # logged-in session (mode=storage_state)
    # Guest session saved by scripts/save_session.py, loaded if the file exists.
    session_state_path: Path = Path("auth/session.json")
    username: SecretStr | None = None
    password: SecretStr | None = None


class SearchSettings(BaseModel):
    use_header_search: bool = False
    use_ui_price_filter: bool = True
    buy_it_now_only: bool = True
    max_pages: int = 5
    range_price_strategy: Literal["max", "min"] = "max"


class CartSettings(BaseModel):
    # "items" = eBay's "Items (N)" line (item prices only); "subtotal" = eBay's "Subtotal" (items + shipping)
    compare_field: Literal["items", "subtotal"] = "items"
    clear_before_test: bool = True


class ArtifactSettings(BaseModel):
    screenshots_dir: Path = Path("reports/screenshots")
    traces_dir: Path = Path("reports/traces")
    tracing: bool = True


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


class YamlProfileSource(PydanticBaseSettingsSource):
    """Loads default.yaml deep-merged with the active profile."""

    def __init__(self, settings_cls: type[BaseSettings], env_name: str) -> None:
        super().__init__(settings_cls)
        self._data = _deep_merge(
            _read_yaml(CONFIG_DIR / "default.yaml"),
            _read_yaml(CONFIG_DIR / "profiles" / f"{env_name}.yaml"),
        )

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._data.items() if k in self.settings_cls.model_fields}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EBAY_", env_nested_delimiter="__", extra="ignore")

    env: str = "local"
    base_url: str = "https://www.ebay.com"
    cart_url: str = "https://cart.ebay.com"
    currency: str = "ILS"
    random_seed: int | None = 42
    data_file: Path = Path("data/search_cases.yaml")
    bot_challenge_action: Literal["wait", "skip", "fail"] = "wait"
    bot_challenge_wait_s: int = 120
    bot_block_reload_retries: int = 2
    bot_challenge_auto_clear_s: int = 20

    browser: BrowserSettings = BrowserSettings()
    auth: AuthSettings = AuthSettings()
    search: SearchSettings = SearchSettings()
    cart: CartSettings = CartSettings()
    artifacts: ArtifactSettings = ArtifactSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        env_name = os.getenv("ENV", "local")
        return init_settings, env_settings, YamlProfileSource(settings_cls, env_name)

    @property
    def bot_challenge_wait_ms(self) -> int:
        """Only wait for a person when the browser window is visible."""
        headed = not self.browser.headless
        return self.bot_challenge_wait_s * 1000 if self.bot_challenge_action == "wait" and headed else 0

    def saved_state_file(self) -> Path | None:
        """Storage state to load into the browser context, if any."""
        path = (
            self.auth.storage_state_path
            if self.auth.mode == "storage_state"
            else self.auth.session_state_path
        )
        resolved = self.resolve(path)
        return resolved if resolved.exists() else None

    def resolve(self, path: Path) -> Path:
        """Make a config-relative path absolute (relative to project root)."""
        return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(env=os.getenv("ENV", "local"))
