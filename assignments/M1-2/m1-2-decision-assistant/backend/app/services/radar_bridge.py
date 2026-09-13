"""MAKE 확정 후보 → RADAR `automaker_intake.package()` + `send()` 호출.

DA 가 AutoMaker 로 직접 보내지 않는다. RADAR 가 이미 갖고 있는 계약(package_id·
payload_hash·revision·provenance, 루프백 HTTP)을 **그대로 부른다.** 그래서 AutoMaker 는
DA 의 존재를 몰라도 되고, 포맷은 하나뿐이다(2026-09-11 감사 §M·§Q).

RADAR 코드를 이 프로세스에 import 하지 않는다. RADAR 는 자기 인터프리터(pandas 등)와
자기 cwd 에서 돌아야 하므로 **subprocess 로 RADAR 의 런타임 안에서** 실행하고 결과만
JSON 으로 받는다. 의존성이 섞이지 않고, RADAR 쪽 예외 문구가 그대로 사용자에게 간다.

관문(gate): 보내기 전에 RADAR 가 만든 payload 의 `decision` — 즉 decisions.jsonl 의
마지막 줄 — 이 MAKE 인지 확인한다. 아니면 보내지 않는다. DA 화면의 상태가 아니라
**원장의 상태**가 기준이다.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# RADAR 런타임 안에서 실행되는 스크립트. argv[1] 에 JSON 인자를 받는다.
# 표준출력 마지막 줄이 결과 JSON 이다 (RADAR 코드가 앞에서 무언가 print 해도 안전).
_RUNNER = r"""
import json, sys
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
out = {"ok": False}
try:
    from src import automaker_intake, config, source_pack
    from pathlib import Path
    import csv
    root = Path(args["root"])
    video_id, channel_id = args["video_id"], args["channel_id"]

    # Source Pack — RADAR UI(handoff_ui.py:233) 와 같은 규칙. 사람이 RADAR 에서 검토·선택해 둔
    # 묶음이 유효하면 그 hash 를 넘겨 동봉·검증하고, 없거나 무효면 '' 로 소재·브리프만 보낸다.
    # DA 가 묶음을 새로 만들지는 않는다 — 그것은 사람 검토가 붙는 RADAR 의 일이다.
    pack_info = {"included": False, "hash": None, "reason": None}
    expected_hash = ""
    try:
        profiles = json.loads((root / "data/config/channels.json").read_text(encoding="utf-8-sig"))
        profile = next((c for c in profiles if c.get("id") == channel_id), None) or {}
        rows = csv.DictReader((root / "data/raw/videos.csv").read_text(encoding="utf-8-sig").splitlines())
        src_channel = next((r.get("channel_id") for r in rows if r.get("video_id") == video_id), None)
        pack = None
        if src_channel and profile.get("profile_family"):
            pack = source_pack.load_selected(root, src_channel, video_id, profile)
            pack_info["reason"] = None if pack else "RADAR 에서 선택된 제작 비교군 Source Pack 없음"
        elif src_channel:
            pack = source_pack.load(root, src_channel, video_id)
            pack_info["reason"] = None if pack else "legacy Source Pack 없음"
        else:
            pack_info["reason"] = "videos.csv 에 원 채널 정보 없음"
        if pack:
            expected_hash = pack["hash"]
            pack_info.update({"included": True, "hash": pack["hash"],
                              "cohort_hash": (pack.get("production_context") or {}).get("cohort_hash")})
    except Exception as exc:  # 무효 묶음(프로필·taxonomy·원문 변경 등) — 보내지 않고 이유만 남긴다
        expected_hash = ""
        pack_info["reason"] = "Source Pack 무효: " + str(exc)
    out["source_pack"] = pack_info

    payload = automaker_intake.build_payload(
        root, video_id, channel_id, "material", expected_source_pack_hash=expected_hash)

    # Channel Identity(승인본) 를 target_channel 에 싣는다. AutoMaker 의 persona draft-input 이
    # target_channel 을 근거로 쓰므로, 페르소나가 패키지 1건이 아니라 채널 기준에서 나온다.
    out["channel_identity"] = {"included": False, "reason": None}
    try:
        ipath = root / "data" / "config" / "channel_identity" / (channel_id + ".json")
        if ipath.is_file():
            identity = json.loads(ipath.read_text(encoding="utf-8"))
            if identity.get("status") == "approved":
                keys = ("identity_version", "problem_space", "expectations", "pillars", "boundary",
                        "narrator_pool", "approved_at", "built_on_profile_version")
                payload["target_channel"]["identity"] = {k: identity.get(k) for k in keys}
                out["channel_identity"] = {"included": True, "identity_version": identity.get("identity_version")}
            else:
                out["channel_identity"]["reason"] = "Identity 가 제안 상태 — 승인 전에는 싣지 않는다"
        else:
            out["channel_identity"]["reason"] = "Channel Identity 없음"
    except Exception as exc:
        out["channel_identity"]["reason"] = "Identity 읽기 실패: " + str(exc)

    decision = payload.get("decision") or {}
    if decision.get("decision") != "MAKE":
        out["error"] = ("RADAR 원장(decisions.jsonl)의 마지막 결정이 MAKE 가 아닙니다: "
                        + str(decision.get("decision") or "기록 없음") + " — 보내지 않았습니다.")
        out["gate"] = "not_make"
    else:
        envelope = automaker_intake.package_payload(payload, root / "data" / "automaker-outbox")
        out.update({
            "package_id": envelope["package_id"], "revision": envelope["revision"],
            "payload_hash": envelope["payload_hash"], "created_at": envelope["created_at"],
            "decision_id": decision.get("decision_id"), "decision_revision": decision.get("revision"),
        })
        if args.get("send", True):
            receipt = automaker_intake.send(envelope, args["automaker_url"])
            out["receipt"] = receipt
            out["ok"] = bool(receipt.get("ok"))
            if not out["ok"]:
                out["error"] = "AutoMaker 가 거부: " + str(receipt.get("error") or receipt)
        else:
            out["ok"] = True
            out["receipt"] = None
except Exception as exc:
    out["error"] = f"{type(exc).__name__}: {exc}"
print("\n" + json.dumps(out, ensure_ascii=False))
"""


class RadarBridge:
    def __init__(self, root: str | Path | None, *, automaker_url: str, python: str = "python") -> None:
        self.root = Path(root) if root else None
        self.automaker_url = automaker_url.rstrip("/")
        self.python = python or "python"

    @property
    def available(self) -> bool:
        return bool(self.root and (self.root / "src" / "automaker_intake.py").is_file())

    def intake_link(self, package_id: str) -> str:
        # RADAR handoff_ui 가 쓰는 것과 같은 AutoMaker 확인 화면.
        return f"{self.automaker_url}/radar-intake.html?package_id={package_id}"

    def package_and_send(self, video_id: str, channel_id: str, *, send: bool = True) -> dict[str, Any]:
        if not self.available:
            return {"ok": False, "error": "RADAR_ROOT 가 없거나 src/automaker_intake.py 를 찾을 수 없습니다."}
        args = json.dumps({
            "root": str(self.root), "video_id": video_id, "channel_id": channel_id,
            "automaker_url": self.automaker_url, "send": send,
        }, ensure_ascii=False)
        try:
            proc = subprocess.run(
                [self.python, "-X", "utf8", "-c", _RUNNER, args],
                cwd=str(self.root), capture_output=True, text=True, encoding="utf-8", timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": f"RADAR 실행 실패: {exc}"}
        last = (proc.stdout or "").strip().splitlines()
        if not last:
            return {"ok": False, "error": f"RADAR 가 응답하지 않음 (exit {proc.returncode}): {(proc.stderr or '')[-400:]}"}
        try:
            result = json.loads(last[-1])
        except json.JSONDecodeError:
            return {"ok": False, "error": f"RADAR 응답 해석 실패: {last[-1][:200]}"}
        if result.get("package_id"):
            result["link"] = self.intake_link(result["package_id"])
        result["automaker_url"] = self.automaker_url
        return result

    def inbox_item(self, package_id: str) -> dict[str, Any] | None:
        """AutoMaker 수신함에서 이 패키지의 현재 상태(받은 revision·프로젝트 연결·project 의 revision)."""
        import urllib.request

        try:
            with urllib.request.urlopen(self.automaker_url + "/api/radar/intake", timeout=20) as r:
                data = json.load(r)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"AutoMaker 수신함 조회 실패: {exc}"}
        item = next((x for x in data.get("items", []) if x.get("package_id") == package_id), None)
        if not item:
            return None
        return {
            "package_id": package_id, "received_revision": item.get("revision"),
            "project_path": item.get("project_path"), "source_revision": item.get("source_revision"),
            "binding": (item.get("binding") or {}).get("state"),
        }

    def link_revision(self, package_id: str, revision: int) -> dict[str, Any]:
        """AutoMaker `continue` — 새 revision 을 프로젝트에 반영(불변 보관 `.radar-intake/<rev>.json`).

        **이미 연결된 프로젝트에만** 부른다. 처음 받는 패키지는 사람이 AutoMaker 에서 제작 채널을
        고르고 확인해야 하며(binding_action), DA 가 그 선택을 대신하지 않는다.
        AutoMaker 는 사용자 편집을 지키기 위해 project.json 의 radar_intake.revision 을 올리지 않는다 —
        `source_revision`(프로젝트) 과 `received_revision`(반영된 최신) 을 둘 다 돌려준다.
        """
        import urllib.error
        import urllib.request

        state = self.inbox_item(package_id)
        if not state or state.get("error"):
            return {"ok": False, "error": (state or {}).get("error") or "AutoMaker 수신함에 이 패키지가 없습니다."}
        if not state.get("project_path"):
            return {"ok": False, "needs_human": True,
                    "error": "아직 AutoMaker 프로젝트에 연결되지 않은 패키지입니다. AutoMaker 에서 제작 채널을 확인해 연결하세요.",
                    "link": self.intake_link(package_id)}
        body = json.dumps({"package_id": package_id, "revision": revision}).encode()
        req = urllib.request.Request(self.automaker_url + "/api/radar/intake/continue", body,
                                     {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.load(r)
        except urllib.error.HTTPError as exc:
            try:
                res = json.load(exc)
            except Exception:  # noqa: BLE001
                res = {"ok": False, "error": f"HTTP {exc.code}"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"AutoMaker continue 호출 실패: {exc}"}
        if not res.get("ok"):
            return {"ok": False, "error": "AutoMaker 가 반영을 거부: " + str(res.get("error"))}
        return {"ok": True, "project_path": res.get("project_path"),
                "source_revision": res.get("source_revision"), "received_revision": res.get("received_revision"),
                "channel_mode": res.get("channel_mode")}

    def intake_command(self, action: str, body: dict[str, Any]) -> dict[str, Any]:
        """AutoMaker `/api/radar/intake/<action>` — 거부 사유를 그대로 돌려준다."""
        import urllib.error
        import urllib.request

        req = urllib.request.Request(f"{self.automaker_url}/api/radar/intake/{action}",
                                     json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                     {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            try:
                return json.load(exc)
            except Exception:  # noqa: BLE001
                return {"ok": False, "error": f"HTTP {exc.code}"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"AutoMaker {action} 호출 실패: {exc}"}

    def persona_draft_input(self, package_id: str) -> dict[str, Any]:
        """AutoMaker 가 정한 프롬프트·근거·revision. DA 는 이 프롬프트를 고치지 않는다."""
        return self.intake_command("draft-input", {"package_id": package_id})

    def persona_save_draft(self, package_id: str, revision: int, draft: dict[str, Any]) -> dict[str, Any]:
        return self.intake_command("save-draft", {"package_id": package_id, "revision": revision, "draft": draft})

    def persona_approve(self, package_id: str, draft_hash: str) -> dict[str, Any]:
        """사람의 승인. AutoMaker 가 근거→정체성으로 승격하는 유일한 경로."""
        return self.intake_command("approve-draft", {"package_id": package_id, "draft_hash": draft_hash})

    def persona_state(self, package_id: str) -> dict[str, Any]:
        """수신함에서 초안 유무·hash·프로젝트 persona 상태."""
        import urllib.request

        try:
            with urllib.request.urlopen(self.automaker_url + "/api/radar/intake", timeout=20) as r:
                data = json.load(r)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"AutoMaker 수신함 조회 실패: {exc}"}
        item = next((x for x in data.get("items", []) if x.get("package_id") == package_id), None)
        if not item:
            return {"error": "AutoMaker 수신함에 이 패키지가 없습니다."}
        out: dict[str, Any] = {"revision": item.get("revision"), "project_path": item.get("project_path"),
                               "draft": item.get("draft"), "draft_hash": item.get("draft_hash")}
        try:
            proj = json.load(open(Path(item["project_path"]) / "project.json", encoding="utf-8"))
            genre = proj.get("genre") or {}
            out.update({"radar_draft": bool(genre.get("radar_draft")), "persona_status": genre.get("persona_status"),
                        "channel_persona": genre.get("channelPersona"), "benchmark_url": genre.get("benchmarkUrl")})
        except Exception:  # noqa: BLE001
            pass
        return out

    def sent_by_assistant(self) -> list[dict[str, Any]]:
        """outbox.sqlite3 에서 DA 결정이 실린 패키지만. 새 파일을 만들지 않고 RADAR 저널을 읽는다."""
        import sqlite3

        if not self.root:
            return []
        db = self.root / "data" / "automaker-outbox" / "outbox.sqlite3"
        if not db.is_file():
            return []
        rows: list[dict[str, Any]] = []
        try:
            with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
                bodies = conn.execute("SELECT body FROM packages ORDER BY revision DESC").fetchall()
        except sqlite3.Error:
            return []
        for (body,) in bodies:
            try:
                env = json.loads(body)
            except (TypeError, json.JSONDecodeError):
                continue
            payload = env.get("payload") or {}
            decision = payload.get("decision") or {}
            if decision.get("producer") != "decision-assistant":
                continue
            rows.append({
                "package_id": env.get("package_id"), "revision": env.get("revision"),
                "created_at": env.get("created_at"), "payload_hash": env.get("payload_hash"),
                "radar_id": payload.get("opportunity_id"),
                "channel": (payload.get("target_channel") or {}).get("id"),
                "topic": payload.get("topic"),
                "decision": decision.get("decision"), "decision_id": decision.get("decision_id"),
                "decision_revision": decision.get("revision"), "note": decision.get("note"),
                "link": self.intake_link(env.get("package_id") or ""),
            })
        rows.sort(key=lambda r: (r["created_at"] or ""), reverse=True)
        return rows
