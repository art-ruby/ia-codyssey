"""프로젝트 이름과 기본 프로젝트 설정을 한 저장소 변경으로 유지한다."""
from __future__ import annotations

import copy
import hashlib
import uuid

from app.core.errors import NoChange
from app.core.context import RequestContext
from app.core.firestore import (FirestoreStore, MemoryStore, NotFound, VersionConflict,
                                _check_doc_id, _new_doc, _owned, _user_fields,
                                _valid_doc_id, now_utc)


class DuplicateProjectName(NoChange):
    pass


class TooManyProjects(NoChange):
    pass


class InvalidDefaultProject(NoChange):
    pass


def settings_id(ctx: RequestContext) -> str:
    digest = hashlib.sha256(f"{ctx.owner_id}\n{ctx.mode}".encode()).hexdigest()[:40]
    return f"settings-{digest}"


def _name_key(name: str) -> str:
    return " ".join(name.split()).casefold()


def _check_name(projects: list[dict], name: str, exclude_id: str | None = None):
    if any(p.get("name_key") == _name_key(name) and p["id"] != exclude_id for p in projects):
        raise DuplicateProjectName()


def _apply_project(projects: list[dict], current: dict | None, ctx: RequestContext,
                   name: str | None, description: str | None, active: bool | None,
                   expected_version: int | None) -> dict:
    if current is None:
        if len(projects) >= 100:
            raise TooManyProjects()
        assert name is not None
        _check_name(projects, name)
        return _new_doc(ctx, {"name": name, "name_key": _name_key(name),
                              "description": description or "", "active": True}, uuid.uuid4().hex)
    if current["version"] != expected_version:
        raise VersionConflict(current["version"])
    if name is not None:
        _check_name(projects, name, current["id"])
        current["name"] = name
        current["name_key"] = _name_key(name)
    if description is not None:
        current["description"] = description
    if active is not None:
        current["active"] = active
    current["version"] += 1
    current["updated_at"] = now_utc()
    return current


def _clear_default(settings: dict | None, project: dict) -> dict | None:
    if settings and project.get("active") is False and settings.get("default_project_id") == project["id"]:
        settings["default_project_id"] = None
        settings["version"] += 1
        settings["updated_at"] = now_utc()
        return settings
    return None


def change_project(store, ctx: RequestContext, project_id: str | None,
                   expected_version: int | None, changes: dict) -> dict:
    if project_id is not None:
        _check_doc_id("projects", project_id)
    if isinstance(store, MemoryStore):
        with store._lock:
            projects = [copy.deepcopy(p) for p in store._docs["projects"].values() if _owned(p, ctx)]
            current = copy.deepcopy(store._docs["projects"].get(project_id)) if project_id else None
            if project_id and not _owned(current, ctx):
                raise NotFound("projects")
            project = _apply_project(projects, current, ctx, changes.get("name"),
                                     changes.get("description"), changes.get("active"), expected_version)
            settings = copy.deepcopy(store._docs["settings"].get(settings_id(ctx)))
            cleared = _clear_default(settings, project)
            store._docs["projects"][project["id"]] = copy.deepcopy(project)
            if cleared:
                store._docs["settings"][settings_id(ctx)] = cleared
            return project

    if not isinstance(store, FirestoreStore):
        raise TypeError("unsupported store")
    from google.cloud import firestore as gcf
    from google.cloud.firestore_v1 import FieldFilter

    lock_ref = store._db.collection("project_state_locks").document(settings_id(ctx))
    setting_ref = store._ref("settings", settings_id(ctx))
    project_ref = store._ref("projects", project_id or uuid.uuid4().hex)
    query = (store._db.collection("projects")
             .where(filter=FieldFilter("owner_id", "==", ctx.owner_id))
             .where(filter=FieldFilter("mode", "==", ctx.mode)))

    @gcf.transactional
    def run(tx):
        lock_ref.get(transaction=tx)
        snapshots = list(tx.get(query))
        projects = [s.to_dict() for s in snapshots]
        current = next((copy.deepcopy(p) for p in projects if p["id"] == project_id), None)
        if project_id and current is None:
            raise NotFound("projects")
        setting_snap = setting_ref.get(transaction=tx)
        settings = setting_snap.to_dict() if setting_snap.exists else None
        project = _apply_project(projects, current, ctx, changes.get("name"),
                                 changes.get("description"), changes.get("active"), expected_version)
        if not project_id:
            project["id"] = project_ref.id
        cleared = _clear_default(settings, project)
        tx.set(project_ref, project)
        if cleared:
            tx.set(setting_ref, cleared)
        tx.set(lock_ref, {"revision": uuid.uuid4().hex})
        return project

    return run(store._db.transaction())


def save_settings(store, ctx: RequestContext, expected_version: int, data: dict) -> dict:
    project_id = data.get("default_project_id")
    if project_id is not None and not _valid_doc_id(project_id):
        raise InvalidDefaultProject()
    if isinstance(store, MemoryStore):
        with store._lock:
            project = store._docs["projects"].get(project_id) if project_id else None
            if project_id and (not _owned(project, ctx) or not project.get("active", True)):
                raise InvalidDefaultProject()
            current = store._docs["settings"].get(settings_id(ctx))
            return _save_settings_doc(ctx, current, expected_version, data,
                                      lambda doc: store._docs["settings"].__setitem__(doc["id"], copy.deepcopy(doc)))

    if not isinstance(store, FirestoreStore):
        raise TypeError("unsupported store")
    from google.cloud import firestore as gcf

    lock_ref = store._db.collection("project_state_locks").document(settings_id(ctx))
    setting_ref = store._ref("settings", settings_id(ctx))
    project_ref = store._ref("projects", project_id) if project_id else None

    @gcf.transactional
    def run(tx):
        lock_ref.get(transaction=tx)
        project_snap = project_ref.get(transaction=tx) if project_ref else None
        project = project_snap.to_dict() if project_snap and project_snap.exists else None
        if project_id and (not _owned(project, ctx) or not project.get("active", True)):
            raise InvalidDefaultProject()
        setting_snap = setting_ref.get(transaction=tx)
        current = setting_snap.to_dict() if setting_snap.exists else None
        doc = _save_settings_doc(ctx, current, expected_version, data, lambda _: None)
        tx.set(setting_ref, doc)
        tx.set(lock_ref, {"revision": uuid.uuid4().hex})
        return doc

    return run(store._db.transaction())


def _save_settings_doc(ctx, current, expected_version, data, write):
    if current is None:
        if expected_version != 0:
            raise VersionConflict(0)
        doc = _new_doc(ctx, data, settings_id(ctx))
    else:
        if current["version"] != expected_version:
            raise VersionConflict(current["version"])
        doc = {**current, **_user_fields(data), "version": current["version"] + 1,
               "updated_at": now_utc()}
    write(doc)
    return copy.deepcopy(doc)
