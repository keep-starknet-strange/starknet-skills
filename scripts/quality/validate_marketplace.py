#!/usr/bin/env python3
"""Validate Claude plugin marketplace metadata consistency."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PATH = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} contains invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return obj


def main() -> int:
    errors: list[str] = []

    if not PLUGIN_PATH.exists():
        errors.append(f"missing {PLUGIN_PATH}")
    if not MARKETPLACE_PATH.exists():
        errors.append(f"missing {MARKETPLACE_PATH}")
    if errors:
        print("Marketplace validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1

    try:
        plugin = load_json(PLUGIN_PATH)
    except (OSError, ValueError) as exc:
        errors.append(f"invalid {PLUGIN_PATH}: {exc}")
        plugin = {}
    try:
        marketplace = load_json(MARKETPLACE_PATH)
    except (OSError, ValueError) as exc:
        errors.append(f"invalid {MARKETPLACE_PATH}: {exc}")
        marketplace = {}

    if errors:
        print("Marketplace validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1

    plugin_name = plugin.get("name")
    plugin_version = plugin.get("version")

    if not isinstance(plugin_name, str) or not plugin_name:
        errors.append("plugin.json missing non-empty 'name'")
    if not isinstance(plugin_version, str) or not plugin_version:
        errors.append("plugin.json missing non-empty 'version'")

    market_name = marketplace.get("name")
    market_version = (marketplace.get("metadata") or {}).get("version")
    plugins = marketplace.get("plugins")

    if not isinstance(market_name, str) or not market_name:
        errors.append("marketplace.json missing non-empty 'name'")
    if not isinstance(market_version, str) or not market_version:
        errors.append("marketplace.json metadata.version missing/non-string")
    if not isinstance(plugins, list) or not plugins:
        errors.append("marketplace.json plugins must be a non-empty array")

    matched = None
    if isinstance(plugins, list) and isinstance(plugin_name, str) and plugin_name:
        for entry in plugins:
            if isinstance(entry, dict) and entry.get("name") == plugin_name:
                matched = entry
                break

    if matched is None:
        errors.append(f"marketplace.json does not contain plugin entry for '{plugin_name}'")
    else:
        if matched.get("source") != "./":
            errors.append("marketplace plugin source for root plugin must be './'")
        if matched.get("version") != plugin_version:
            errors.append(
                f"version mismatch: plugin.json={plugin_version} vs marketplace.plugins[{plugin_name}].version={matched.get('version')}"
            )

    if plugin_version and market_version and plugin_version != market_version:
        errors.append(
            f"version mismatch: plugin.json={plugin_version} vs marketplace.metadata.version={market_version}"
        )

    if market_name and plugin_name and market_name != plugin_name:
        errors.append(f"name mismatch: marketplace.name={market_name} vs plugin.name={plugin_name}")

    if errors:
        print("Marketplace validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1

    print(
        f"OK: marketplace metadata is consistent for plugin '{plugin_name}' at version {plugin_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
