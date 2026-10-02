"""Export format v1: YAML for types and the profile, markdown for entries.

```text
lapidarium.yaml               format version
profile.yaml                  profile and links
types/<key>.yaml              type settings and fields
content/<type>/<slug>.md      frontmatter (built-ins, metadata, parts, relations,
                              syndication); text parts are the body, in order
assets.yaml                   alt text per asset path
<asset path>                  the files, at the paths entries refer to
```

Keys left at their default are not written, and may be left out by hand.
"""

from __future__ import annotations

import datetime as dt
import shutil
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, override

import yaml
from pydantic import TypeAdapter, ValidationError

from lapidarium.pacts import (
    BUILTIN_DEFAULTS,
    EXPORT_FORMAT_VERSION,
    FIELD_DEFAULTS,
    TYPE_DEFAULTS,
    AssetData,
    BundleValidationError,
    ContentStoreProtocol,
    EntryData,
    EntryTypeData,
    LinkData,
    NotFoundError,
    PartKind,
    ProfileData,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping

    from lapidarium.pacts import ContentBundle, SettingDefault

DEMOS = Path(__file__).resolve().parent / "demos"
MANIFEST = "lapidarium.yaml"
PART_BREAK = "<!-- part -->"
_FENCE = "---\n"
ASSETS = "assets"

type Json = str | int | float | bool | dt.date | list[Json] | dict[str, Json] | None


def _as_json(defaults: Mapping[str, SettingDefault]) -> dict[str, Json]:
    return {k: [*v] if isinstance(v, tuple) else v for k, v in defaults.items()}


_TYPE_DEFAULTS = {**_as_json(TYPE_DEFAULTS), "fields": []}
_FIELD_DEFAULTS = _as_json(FIELD_DEFAULTS)
_ENTRY_DEFAULTS: dict[str, Json] = {
    **BUILTIN_DEFAULTS,
    "external_url": "",
    "status": "draft",
    "featured": False,
    "hide_from_whats_new": False,
    "license": "",
    "cover": "",
    "tags": [],
    "metadata": {},
    "parts": [],
    "relations": [],
    "syndication": [],
    "created_at": None,
    "updated_at": None,
}
_PART_DEFAULTS: dict[str, Json] = {
    "text": "",
    "url": "",
    "asset": "",
    "caption": "",
    "options": {},
}
_PROFILE_DEFAULTS: dict[str, Json] = {
    "handle": "",
    "tagline": "",
    "photo": "",
    "bio": "",
    "email": "",
}

_TYPE = TypeAdapter(EntryTypeData)
_ENTRY = TypeAdapter(EntryData)
_PROFILE = TypeAdapter(ProfileData)
_LINKS = TypeAdapter(list[LinkData])


class ContentFilesStore(ContentStoreProtocol):
    def __init__(self, demos: Path = DEMOS) -> None:
        self._demos = demos

    @override
    def demo_names(self) -> tuple[str, ...]:
        return tuple(sorted(p.name for p in self._demos.iterdir() if p.is_dir()))

    @override
    def read_demo(self, name: str) -> ContentBundle:
        if name not in self.demo_names():
            raise NotFoundError(name)
        return self.read(self._demos / name)

    @override
    def read(self, root: Path) -> ContentBundle:
        errors: dict[str, list[str]] = {}
        with _collect(errors, MANIFEST):
            manifest = (
                yaml.safe_load((root / MANIFEST).read_text(encoding="utf-8")) or {}
            )
            if manifest.get("format") != EXPORT_FORMAT_VERSION:
                msg = f"Expected format {EXPORT_FORMAT_VERSION}."
                raise ValueError(msg)
        if errors:
            raise BundleValidationError(errors)
        bundle: ContentBundle = {
            "profile": None,
            "links": [],
            "types": [],
            "entries": [],
            "assets": [],
        }
        if (root / "profile.yaml").exists():
            with _collect(errors, "profile.yaml"):
                raw = yaml.safe_load(
                    (root / "profile.yaml").read_text(encoding="utf-8")
                )
                bundle["links"] = _LINKS.validate_python(raw.pop("links", []))
                bundle["profile"] = _PROFILE.validate_python(_PROFILE_DEFAULTS | raw)
        for path in sorted((root / "types").glob("*.yaml")):
            with _collect(errors, f"types/{path.name}"):
                bundle["types"].append(_read_type(path))
        for path in sorted((root / "content").glob("*/*.md")):
            with _collect(errors, f"content/{path.parent.name}/{path.name}"):
                bundle["entries"].append(_read_entry(path))
        if (root / "assets.yaml").exists():
            with _collect(errors, "assets.yaml"):
                bundle["assets"] = [
                    _read_asset(root, str(item["path"]), alt=str(item.get("alt", "")))
                    for item in yaml.safe_load(
                        (root / "assets.yaml").read_text(encoding="utf-8")
                    )
                ]
        if errors:
            raise BundleValidationError(errors)
        return bundle

    @override
    def write(self, root: Path, bundle: ContentBundle) -> None:
        for owned in ("types", "content", ASSETS):
            shutil.rmtree(root / owned, ignore_errors=True)
        (root / "types").mkdir(parents=True)
        (root / MANIFEST).write_text(
            _dump({"format": EXPORT_FORMAT_VERSION}), encoding="utf-8"
        )
        if bundle["profile"]:
            profile = _PROFILE.dump_python(bundle["profile"], mode="python")
            profile["links"] = _LINKS.dump_python(bundle["links"], mode="python")
            (root / "profile.yaml").write_text(_dump(profile), encoding="utf-8")
        else:
            (root / "profile.yaml").unlink(missing_ok=True)
        for entry_type in bundle["types"]:
            path = root / "types" / f"{entry_type['key']}.yaml"
            path.write_text(_type_file(entry_type), encoding="utf-8")
        for entry in bundle["entries"]:
            path = root / "content" / entry["type"] / f"{entry['slug']}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_entry_file(entry), encoding="utf-8")
        alts: Json = [{"path": a["path"], "alt": a["alt"]} for a in bundle["assets"]]
        (root / "assets.yaml").write_text(_dump(alts), encoding="utf-8")
        for asset in bundle["assets"]:
            path = root / _safe_path(asset["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(asset["content"])


@contextmanager
def _collect(errors: dict[str, list[str]], where: str) -> Generator[None]:
    try:
        yield
    except ValidationError as exc:
        errors.setdefault(where, []).extend(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        errors.setdefault(where, []).append(str(exc))


class _Dumper(yaml.SafeDumper):
    """Safe YAML that writes enum members as their plain values."""


_Dumper.add_multi_representer(
    StrEnum, lambda dumper, member: dumper.represent_str(member.value)
)


def _dump(data: Json) -> str:
    return yaml.dump(data, Dumper=_Dumper, allow_unicode=True, sort_keys=False)


def _without_defaults(data: dict[str, Json], defaults: dict[str, Json]) -> Json:
    return {k: v for k, v in data.items() if k not in defaults or v != defaults[k]}


def _safe_path(path: str) -> PurePosixPath:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or pure.parts[:1] != (ASSETS,):
        msg = f"Asset paths stay under {ASSETS}/, got {path!r}."
        raise ValueError(msg)
    return pure


def _type_file(entry_type: EntryTypeData) -> str:
    data = _TYPE.dump_python(entry_type, mode="python")
    data["fields"] = [_without_defaults(f, _FIELD_DEFAULTS) for f in data["fields"]]
    return _dump(_without_defaults(data, _TYPE_DEFAULTS))


def _read_type(path: Path) -> EntryTypeData:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    fields = [_FIELD_DEFAULTS | field for field in loaded.pop("fields", [])]
    return _TYPE.validate_python(_TYPE_DEFAULTS | loaded | {"fields": fields})


def _entry_file(entry: EntryData) -> str:
    data = _ENTRY.dump_python(entry, mode="python")
    data["parts"] = [
        _without_defaults(
            {
                k: v
                for k, v in part.items()
                if part["kind"] != PartKind.TEXT or k != "text"
            },
            _PART_DEFAULTS,
        )
        for part in data["parts"]
    ]
    data["relations"] = [
        {"role": r["role"], "to": f"{r['target_type']}/{r['target_slug']}"}
        for r in data["relations"]
    ]
    body = f"\n\n{PART_BREAK}\n\n".join(
        part["text"].strip() for part in entry["parts"] if part["kind"] == PartKind.TEXT
    )
    ordered = {key: data[key] for key in ("title", "summary", *_ENTRY_DEFAULTS)}
    front = _dump(_without_defaults(ordered, _ENTRY_DEFAULTS))
    return f"{_FENCE}{front}{_FENCE}" + (f"\n{body}\n" if body else "")


def _read_entry(path: Path) -> EntryData:
    text = path.read_text(encoding="utf-8")
    front, fence, body = text.removeprefix(_FENCE).partition(f"\n{_FENCE}")
    if not text.startswith(_FENCE) or not fence:
        msg = "Expected YAML frontmatter between --- lines."
        raise ValueError(msg)
    loaded = yaml.safe_load(front) or {}
    parts = [_PART_DEFAULTS | part for part in loaded.pop("parts", [])]
    text_parts = [part for part in parts if part.get("kind") == PartKind.TEXT]
    texts = [s.strip() for s in body.split(PART_BREAK)] if body.strip() else []
    if len(text_parts) != len(texts):
        msg = f"{len(text_parts)} text parts listed, {len(texts)} in the body."
        raise ValueError(msg)
    for part, section in zip(text_parts, texts, strict=True):
        part["text"] = section
    relations = [
        dict(
            zip(
                ("target_type", "target_slug"),
                str(relation["to"]).split("/", 1),
                strict=True,
            ),
            role=relation["role"],
        )
        for relation in loaded.pop("relations", [])
    ]
    return _ENTRY.validate_python(
        _ENTRY_DEFAULTS
        | loaded
        | {
            "type": path.parent.name,
            "slug": path.stem,
            "parts": parts,
            "relations": relations,
        }
    )


def _read_asset(root: Path, path: str, *, alt: str) -> AssetData:
    return {"path": path, "alt": alt, "content": (root / _safe_path(path)).read_bytes()}
