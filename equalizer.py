#!/usr/bin/env python3

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PRESET_NAME = "live_eq"
ALTERNATE_PRESET_NAME = "live_eq_alt"
PRESETS = {
    "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Bass": [5, 7, 5, 2, 1, 0, 0, 0, 1, 2],
    "Treble": [-2, -1, 0, 1, 2, 3, 4, 5, 6, 6],
    "Vocal": [-2, -1, 1, 3, 5, 5, 4, 2, 1, 0],
    "Pop": [2, 4, 2, 0, 1, 2, 4, 2, 1, 2],
    "Rock": [5, 4, 2, -1, -2, -1, 2, 4, 5, 6],
    "Jazz": [3, 3, 1, 1, 1, 1, 2, 1, 2, 3],
    "Classic": [0, 1, 2, 2, 2, 2, 1, 2, 3, 4],
}
FREQUENCIES = [
    32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
    1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
    12500, 16000, 20000, 22000, 24000, 24000,
]
SLIDER_BANDS = {0: 0, 1: 3, 2: 6, 3: 9, 4: 12, 5: 15, 6: 18, 7: 21, 8: 24, 9: 27}
DEFAULT_GAINS = [0] * 10


def state_path():
    state_home = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return state_home / "omarchy" / "serpantinum-equalizer.json"


def preset_path(name):
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return data_home / "easyeffects" / "output" / f"{name}.json"


def state_for(gains=None, preset="Flat", pending=False, profile=PRESET_NAME):
    state = {f"b{i + 1}": value for i, value in enumerate(gains or DEFAULT_GAINS)}
    state.update({"preset": preset, "pending": pending, "profile": profile})
    return state


def validate_gains(values):
    if not isinstance(values, list) or len(values) != 10:
        raise ValueError("Se esperaban exactamente diez bandas.")
    gains = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Cada ganancia debe ser un número entre -12 y 12 dB.")
        if not math.isfinite(value) or value < -12 or value > 12:
            raise ValueError("Cada ganancia debe ser un número finito entre -12 y 12 dB.")
        gains.append(int(round(value)))
    return gains


def gains_from_state(state):
    try:
        values = [state[f"b{i}"] for i in range(1, 11)]
    except (KeyError, TypeError) as error:
        raise ValueError("El archivo de estado no contiene las diez bandas.") from error
    return validate_gains(values)


def load_state():
    path = state_path()
    if not path.exists():
        return state_for()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"No se pudo leer el estado del ecualizador: {error}") from error
    gains = gains_from_state(state)
    preset = state.get("preset", "Custom")
    if preset not in (*PRESETS.keys(), "Custom"):
        preset = "Custom"
    pending = state.get("pending", False)
    if not isinstance(pending, bool):
        raise ValueError("El estado del ecualizador contiene un indicador pending inválido.")
    profile = state.get("profile", PRESET_NAME)
    if profile not in (PRESET_NAME, ALTERNATE_PRESET_NAME):
        profile = PRESET_NAME
    return state_for(gains, preset, pending, profile)


def write_json_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(data, temporary, indent=2)
            temporary.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def build_preset(state):
    gains = gains_from_state(state)
    slider_to_gain = {band: gains[index] for index, band in SLIDER_BANDS.items()}
    bands = {}
    for index in range(32):
        bands[f"band{index}"] = {
            "frequency": FREQUENCIES[index],
            "gain": slider_to_gain.get(index, 0),
            "type": "Bell",
            "mode": "RLC (BT)",
            "mute": False,
            "q": 1.0,
            "solo": False,
            "width": 1.0,
            "slope": "x1",
        }
    return {
        "output": {
            "blocklist": [],
            "plugins_order": ["equalizer"],
            "equalizer": {
                "bypass": False,
                "input-gain": 0.0,
                "output-gain": 0.0,
                "left": bands,
                "right": json.loads(json.dumps(bands)),
                "mode": "IIR",
                "num-bands": 32,
                "split-channels": False,
            },
        }
    }


def apply_state(state):
    state["pending"] = True

    executable = shutil.which("easyeffects")
    if executable is None:
        raise RuntimeError(
            "EasyEffects no está instalado o no está en PATH. Instálalo y vuelve a aplicar el ecualizador."
        )
    try:
        current_result = subprocess.run(
            [executable, "-a", "output"],
            check=False,
            capture_output=True,
            text=True,
            timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"No se pudo consultar el perfil activo de EasyEffects: {error}") from error
    if current_result.returncode != 0:
        detail = current_result.stderr.strip() or current_result.stdout.strip()
        raise RuntimeError(
            "No se pudo consultar el perfil activo de EasyEffects."
            + (f" {detail}" if detail else "")
        )
    current_profile = current_result.stdout.strip().splitlines()[-1:]
    current_profile = current_profile[0].removeprefix("output: ").strip() if current_profile else ""
    profile = ALTERNATE_PRESET_NAME if current_profile == PRESET_NAME else PRESET_NAME

    write_json_atomic(preset_path(profile), build_preset(state))
    try:
        result = subprocess.run(
            [executable, "-l", profile],
            check=False,
            capture_output=True,
            text=True,
            timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"No se pudo cargar el perfil en EasyEffects: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "EasyEffects no pudo cargar el preset."
            + (f" {detail}" if detail else "")
        )

    try:
        loaded_result = subprocess.run(
            [executable, "-a", "output"],
            check=False,
            capture_output=True,
            text=True,
            timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"No se pudo verificar el perfil activo de EasyEffects: {error}") from error
    loaded_profile = loaded_result.stdout.strip().splitlines()[-1:]
    loaded_profile = loaded_profile[0].removeprefix("output: ").strip() if loaded_profile else ""
    if loaded_result.returncode != 0 or loaded_profile != profile:
        detail = loaded_result.stderr.strip()
        raise RuntimeError(
            f"EasyEffects no confirmó la carga del perfil {profile}."
            + (f" {detail}" if detail else "")
        )

    state["profile"] = profile
    state["pending"] = False
    write_json_atomic(state_path(), state)
    return state


def parse_args():
    parser = argparse.ArgumentParser(description="Serpantinum equalizer state helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("get")
    set_parser = subparsers.add_parser("set-bands")
    set_parser.add_argument("gains")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("gains", nargs="?")
    preset_parser = subparsers.add_parser("preset")
    preset_parser.add_argument("name", choices=PRESETS)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        state = load_state()
        if args.command == "get":
            pass
        elif args.command == "set-bands":
            state = state_for(validate_gains(json.loads(args.gains)), "Custom", True, state["profile"])
            write_json_atomic(state_path(), state)
        elif args.command == "apply":
            if args.gains:
                state = state_for(validate_gains(json.loads(args.gains)), "Custom", True, state["profile"])
            state = apply_state(state)
        elif args.command == "preset":
            state = state_for(PRESETS[args.name], args.name, True, state["profile"])
            write_json_atomic(state_path(), state)
            state = apply_state(state)
        print(json.dumps(state, separators=(",", ":")))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
