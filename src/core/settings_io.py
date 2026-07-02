"""Export / import of settings, rules and templates as a single JSON bundle."""
from __future__ import annotations

import json
from pathlib import Path

from ..models.repository import get_repository
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger(__name__)

_SECRET_KEYS = {"proxy_user"}  # never export secrets


def export_bundle(path: str | Path) -> None:
    cfg = get_config()
    repo = get_repository()
    settings = {k: v for k, v in cfg.all_settings().items()
                if k not in _SECRET_KEYS}
    bundle = {
        "app": "FunPay AutoResponder",
        "version": 1,
        "settings": settings,
        "rules": [r.to_dict() for r in repo.rules()],
        "templates": [t.to_dict() for t in repo.templates()],
    }
    Path(path).write_text(json.dumps(bundle, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    log.info("Exported configuration bundle to %s", path)


def import_bundle(path: str | Path, *, merge: bool = True) -> None:
    from ..models.rule import Rule
    from ..models.template import Template

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg = get_config()
    repo = get_repository()

    if "settings" in data and isinstance(data["settings"], dict):
        clean = {k: v for k, v in data["settings"].items()
                 if k not in _SECRET_KEYS}
        cfg.update(clean)

    if "templates" in data:
        for row in data["templates"]:
            repo.upsert_template(Template.from_dict(row))
    if "rules" in data:
        for row in data["rules"]:
            repo.upsert_rule(Rule.from_dict(row))
    log.info("Imported configuration bundle from %s (merge=%s)", path, merge)
