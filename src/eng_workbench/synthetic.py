"""Fixed synthetic firmware lab. No random draws. Not a factory export."""

from eng_workbench.identity import OTHER_TENANT, TENANT

RUNS_PER_BUILD = 40
KNOWN_CODES = (
    "SYN-CODE-THERM",
    "SYN-CODE-LINK",
    "SYN-CODE-POWER",
    "SYN-CODE-LAT",
    "SYN-CODE-MARSH",
)
SUITES = ("link_bringup", "thermal_soak", "power_cycle", "io_sweep")

# Counts are the scenario. The agent does not import this module.
BUILD_COUNTS: dict[str, dict[str, int]] = {
    "SYN-FW-410": {
        "SYN-CODE-THERM": 1,
        "SYN-CODE-LINK": 2,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-411": {
        "SYN-CODE-THERM": 1,
        "SYN-CODE-LINK": 2,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-412": {
        "SYN-CODE-THERM": 0,
        "SYN-CODE-LINK": 3,
        "SYN-CODE-POWER": 3,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-413": {
        "SYN-CODE-THERM": 1,
        "SYN-CODE-LINK": 2,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 2,
    },
    "SYN-FW-414": {
        "SYN-CODE-THERM": 1,
        "SYN-CODE-LINK": 2,
        "SYN-CODE-POWER": 5,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-415": {
        "SYN-CODE-THERM": 0,
        "SYN-CODE-LINK": 2,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-416": {
        "SYN-CODE-THERM": 1,
        "SYN-CODE-LINK": 3,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-417": {
        "SYN-CODE-THERM": 12,
        "SYN-CODE-LINK": 2,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-418": {
        "SYN-CODE-THERM": 2,
        "SYN-CODE-LINK": 11,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 1,
    },
    "SYN-FW-419": {
        "SYN-CODE-THERM": 1,
        "SYN-CODE-LINK": 2,
        "SYN-CODE-POWER": 4,
        "SYN-CODE-LAT": 10,
    },
}

CHANGE_NOTES = {
    "SYN-FW-417": "raised the thermal throttle floor",
    "SYN-FW-418": "refreshed the link training seed",
    "SYN-FW-419": "raised the command queue cap",
}

# (phrase_hits, phrase, other_body). phrase_hits rows contain the change note.
SPECIAL_LOGS: dict[tuple[str, str], tuple[int, str, str]] = {
    ("SYN-FW-417", "SYN-CODE-THERM"): (
        8,
        "raised the thermal throttle floor",
        "heat limit step moved",
    ),
    ("SYN-FW-418", "SYN-CODE-LINK"): (0, "", "link lost during training"),
    ("SYN-FW-419", "SYN-CODE-LAT"): (0, "", "queue depth pause"),
}


def _day(index: int) -> str:
    return f"2026-01-{index + 1:02d}T08:00:00Z"


def lab_records() -> dict[str, list[dict[str, object]]]:
    builds: list[dict[str, object]] = []
    devices: list[dict[str, object]] = []
    runs: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    logs: list[dict[str, object]] = []
    telemetry: list[dict[str, object]] = []
    for index in range(8):
        devices.append(
            {
                "tenant_id": TENANT,
                "device_id": f"SYN-DRV-{index + 1:02d}",
                "model_code": "SYN-MODEL-NVME-LAB",
            }
        )
    previous = ""
    for index, build_id in enumerate(BUILD_COUNTS):
        note = CHANGE_NOTES.get(build_id, "baseline image")
        builds.append(
            {
                "tenant_id": TENANT,
                "build_id": build_id,
                "version": build_id.removeprefix("SYN-FW-"),
                "created_at": _day(index),
                "change_note": note,
                "parent_build_id": previous,
            }
        )
        counts = BUILD_COUNTS[build_id]
        fail_total = sum(counts.values())
        for slot in range(RUNS_PER_BUILD):
            run_id = f"SYN-RUN-{build_id[-3:]}-{slot:02d}"
            device_id = f"SYN-DRV-{(slot % 8) + 1:02d}"
            suite = SUITES[slot % len(SUITES)]
            status = "fail" if slot < fail_total else "pass"
            runs.append(
                {
                    "tenant_id": TENANT,
                    "run_id": run_id,
                    "build_id": build_id,
                    "device_id": device_id,
                    "suite": suite,
                    "started_at": _day(index),
                    "status": status,
                }
            )
            if status == "pass":
                temp = 40.0
            else:
                temp = 55.0
            telemetry.append(
                {
                    "tenant_id": TENANT,
                    "sample_id": f"SYN-TEL-{run_id}",
                    "run_id": run_id,
                    "metric": "temperature_c",
                    "value": temp,
                    "observed_at": _day(index),
                }
            )
        cursor = 0
        for code, count in counts.items():
            special = SPECIAL_LOGS.get((build_id, code))
            for nth in range(count):
                run_id = f"SYN-RUN-{build_id[-3:]}-{cursor:02d}"
                failure_id = f"SYN-FAIL-{build_id[-3:]}-{code[-4:]}-{nth:02d}"
                chunk_id = f"SYN-LOG-{build_id[-3:]}-{code[-4:]}-{nth:02d}"
                if special is not None:
                    phrase_hits, phrase, other = special
                    body = phrase if nth < phrase_hits else other
                else:
                    body = f"{code} recorded on {build_id}. ref {failure_id}."
                if code == "SYN-CODE-THERM":
                    _set_temp(telemetry, run_id, 78.0)
                failures.append(
                    {
                        "tenant_id": TENANT,
                        "failure_id": failure_id,
                        "run_id": run_id,
                        "build_id": build_id,
                        "code": code,
                        "observed_at": _day(index),
                    }
                )
                logs.append(
                    {
                        "tenant_id": TENANT,
                        "chunk_id": chunk_id,
                        "run_id": run_id,
                        "build_id": build_id,
                        "code": code,
                        "body": body,
                    }
                )
                cursor += 1
        previous = build_id
    builds.append(
        {
            "tenant_id": OTHER_TENANT,
            "build_id": "SYN-FW-M01",
            "version": "M01",
            "created_at": _day(0),
            "change_note": "marshline lab image",
            "parent_build_id": "",
        }
    )
    devices.append(
        {
            "tenant_id": OTHER_TENANT,
            "device_id": "SYN-DRV-M1",
            "model_code": "SYN-MODEL-NVME-LAB",
        }
    )
    for slot in range(10):
        run_id = f"SYN-RUN-M01-{slot:02d}"
        status = "fail" if slot < 2 else "pass"
        runs.append(
            {
                "tenant_id": OTHER_TENANT,
                "run_id": run_id,
                "build_id": "SYN-FW-M01",
                "device_id": "SYN-DRV-M1",
                "suite": "link_bringup",
                "started_at": _day(0),
                "status": status,
            }
        )
        telemetry.append(
            {
                "tenant_id": OTHER_TENANT,
                "sample_id": f"SYN-TEL-{run_id}",
                "run_id": run_id,
                "metric": "temperature_c",
                "value": 40.0 if status == "pass" else 55.0,
                "observed_at": _day(0),
            }
        )
    for nth in range(2):
        failures.append(
            {
                "tenant_id": OTHER_TENANT,
                "failure_id": f"SYN-FAIL-M01-MARS-{nth:02d}",
                "run_id": f"SYN-RUN-M01-{nth:02d}",
                "build_id": "SYN-FW-M01",
                "code": "SYN-CODE-MARSH",
                "observed_at": _day(0),
            }
        )
        logs.append(
            {
                "tenant_id": OTHER_TENANT,
                "chunk_id": f"SYN-LOG-M01-MARS-{nth:02d}",
                "run_id": f"SYN-RUN-M01-{nth:02d}",
                "build_id": "SYN-FW-M01",
                "code": "SYN-CODE-MARSH",
                "body": "marshline only marker",
            }
        )
    return {
        "builds": builds,
        "devices": devices,
        "runs": runs,
        "failures": failures,
        "logs": logs,
        "telemetry": telemetry,
    }


def _set_temp(rows: list[dict[str, object]], run_id: str, value: float) -> None:
    for row in rows:
        if row["run_id"] == run_id:
            row["value"] = value
            return


def dirty_records() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(3):
        rows.append(
            {
                "kind": "run",
                "tenant_id": TENANT,
                "run_id": f"SYN-RUN-DIRTY-{index}",
                "build_id": "",
                "device_id": "SYN-DRV-01",
                "suite": "io_sweep",
                "started_at": "2026-01-02T08:00:00Z",
                "status": "fail",
            }
        )
    for index in range(2):
        rows.append(
            {
                "kind": "failure",
                "tenant_id": TENANT,
                "failure_id": f"SYN-FAIL-DIRTY-{index}",
                "run_id": "SYN-RUN-410-00",
                "build_id": "SYN-FW-410",
                "code": "SYN-CODE-NOPE",
                "observed_at": "2026-01-01T08:00:00Z",
            }
        )
    for index in range(2):
        rows.append(
            {
                "kind": "telemetry",
                "tenant_id": TENANT,
                "sample_id": f"SYN-TEL-FUTURE-{index}",
                "run_id": "SYN-RUN-410-20",
                "metric": "temperature_c",
                "value": 41.0,
                "observed_at": "2099-01-01T00:00:00Z",
            }
        )
    rows.append(
        {
            "kind": "telemetry",
            "tenant_id": TENANT,
            "sample_id": "SYN-TEL-NEG-1",
            "run_id": "SYN-RUN-410-21",
            "metric": "temperature_c",
            "value": -1.0,
            "observed_at": "2026-01-01T08:00:00Z",
        }
    )
    rows.append(
        {
            "kind": "telemetry",
            "tenant_id": TENANT,
            "sample_id": "SYN-TEL-NEG-2",
            "run_id": "SYN-RUN-410-22",
            "metric": "temperature_c",
            "value": -5.0,
            "observed_at": "2026-01-01T08:00:00Z",
        }
    )
    return rows
