from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
except ImportError:  # pragma: no cover - CLI message handles this at runtime.
    Workbook = None
    load_workbook = None


PXC5_E24_MAX_POINTS = 80
PXC4_E16S_MAX_POINTS = 40
PXC7_E400S_MAX_POINTS = 100
PXC7_E400M_MAX_POINTS = 250


@dataclass
class DdcInput:
    ddc_no: str
    di: int
    do: int
    ai: int
    ao: int
    project: str = ""
    area: str = ""
    equipment: str = ""
    panel_size: str = ""
    controller_override: str = ""
    analog_module: str = ""

    @property
    def total(self) -> int:
        return self.di + self.do + self.ai + self.ao


@dataclass
class DdcSelection:
    source: DdcInput
    controller: str
    txm16d_qty: int
    txm6r_qty: int
    analog_module: str
    analog_module_qty: int
    txs_qty: int
    txa_qty: int
    panel_code: str
    messages: list[str]

    @property
    def module_total(self) -> int:
        return self.txm16d_qty + self.txm6r_qty + self.analog_module_qty


def ceil_div(value: int, divisor: int) -> int:
    if value <= 0:
        return 0
    return math.ceil(value / divisor)


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def int_cell(value: Any, name: str) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(value))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def text_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_inputs(path: Path) -> list[DdcInput]:
    if path.suffix.lower() == ".csv":
        return read_csv_inputs(path)
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return read_excel_inputs(path)
    raise ValueError("Input must be .csv, .xlsx, or .xlsm")


def read_csv_inputs(path: Path) -> list[DdcInput]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            normalized = {normalize_header(k): v for k, v in row.items()}
            if not any(text_cell(v) for v in normalized.values()):
                continue
            rows.append(row_to_input(normalized))
        return rows


def read_excel_inputs(path: Path) -> list[DdcInput]:
    if load_workbook is None:
        raise RuntimeError("openpyxl is required for Excel input")
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    headers = [normalize_header(c.value or "") for c in ws[1]]
    rows = []
    for excel_row in ws.iter_rows(min_row=2, values_only=True):
        normalized = dict(zip(headers, excel_row))
        if not any(text_cell(v) for v in normalized.values()):
            continue
        rows.append(row_to_input(normalized))
    return rows


def row_to_input(row: dict[str, Any]) -> DdcInput:
    ddc_no = text_cell(row.get("ddc_no") or row.get("ddc") or row.get("ddcno"))
    if not ddc_no:
        raise ValueError("DDC-No is required")
    return DdcInput(
        ddc_no=ddc_no,
        di=int_cell(row.get("di"), "DI"),
        do=int_cell(row.get("do"), "DO"),
        ai=int_cell(row.get("ai"), "AI"),
        ao=int_cell(row.get("ao"), "AO"),
        project=text_cell(row.get("project")),
        area=text_cell(row.get("area")),
        equipment=text_cell(row.get("equipment")),
        panel_size=text_cell(row.get("panel_size")),
        controller_override=text_cell(row.get("controller_override")),
        analog_module=text_cell(row.get("analog_module")),
    )


def select_controller(ddc: DdcInput) -> tuple[str, list[str]]:
    if ddc.controller_override:
        return ddc.controller_override, [f"controller override applied: {ddc.controller_override}"]
    if ddc.total <= PXC4_E16S_MAX_POINTS:
        return "PXC4.E16S-2", [f"total {ddc.total} <= {PXC4_E16S_MAX_POINTS}; PXC4.E16S-2 selected"]
    if ddc.total <= PXC5_E24_MAX_POINTS:
        return "PXC5.E24", [f"total {ddc.total} <= {PXC5_E24_MAX_POINTS}; PXC5.E24 selected"]
    if ddc.total <= PXC7_E400S_MAX_POINTS:
        return "PXC7.E400S", [
            f"total {ddc.total} exceeds PXC5.E24 max {PXC5_E24_MAX_POINTS}; PXC7.E400S selected"
        ]
    if ddc.total <= PXC7_E400M_MAX_POINTS:
        return "PXC7.E400M", [
            f"total {ddc.total} exceeds PXC7.E400S max {PXC7_E400S_MAX_POINTS}; PXC7.E400M selected"
        ]
    return "PXC7.E400L", [
        f"total {ddc.total} exceeds PXC7.E400M max {PXC7_E400M_MAX_POINTS}; PXC7.E400L review required"
    ]


def panel_code(panel_size: str) -> str:
    normalized = panel_size.replace(" ", "").replace("*", "x").lower()
    if "900x2180x300" in normalized:
        return "E"
    if "900x1800x300" in normalized:
        return "D"
    if "900x1430x300" in normalized:
        return "C"
    if "800x1150x300" in normalized:
        return "B"
    if "800x880x300" in normalized:
        return "A"
    return ""


def default_panel_code(selection: DdcInput) -> str:
    explicit = panel_code(selection.panel_size)
    if explicit:
        return explicit
    if selection.total > PXC5_E24_MAX_POINTS:
        return "E"
    return "D"


def select_ddc(ddc: DdcInput, default_analog_module: str) -> DdcSelection:
    controller, messages = select_controller(ddc)
    analog_module = (ddc.analog_module or default_analog_module).strip().upper()
    if analog_module in {"U", "8U"}:
        analog_module = "TXM1.8U"
    elif analog_module in {"X", "8X"}:
        analog_module = "TXM1.8X"
    if analog_module not in {"TXM1.8U", "TXM1.8X"}:
        raise ValueError("analog module must be TXM1.8U, TXM1.8X, U, X, 8U, or 8X")

    if analog_module == "TXM1.8X":
        messages.append("analog module is TXM1.8X; use this when 4-20mA points are included")
    else:
        messages.append("analog module is TXM1.8U; use this for 0-10V/passive analog points")

    return DdcSelection(
        source=ddc,
        controller=controller,
        txm16d_qty=ceil_div(ddc.di, 16),
        txm6r_qty=ceil_div(ddc.do, 6),
        analog_module=analog_module,
        analog_module_qty=ceil_div(ddc.ai + ddc.ao, 8),
        txs_qty=1,
        txa_qty=1,
        panel_code=default_panel_code(ddc),
        messages=messages,
    )


def write_csv_output(path: Path, selections: list[DdcSelection]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = summary_rows(selections)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summary_rows(selections: list[DdcSelection]) -> list[dict[str, Any]]:
    rows = []
    for sel in selections:
        ddc = sel.source
        rows.append(
            {
                "DDC-No": ddc.ddc_no,
                "Area": ddc.area,
                "Equipment": ddc.equipment,
                "DI": ddc.di,
                "DO": ddc.do,
                "AI": ddc.ai,
                "AO": ddc.ao,
                "Total": ddc.total,
                "Controller": sel.controller,
                "TXM1.16D": sel.txm16d_qty,
                "TXM1.6R": sel.txm6r_qty,
                sel.analog_module: sel.analog_module_qty,
                "TXS1.12F10": sel.txs_qty,
                "TXA1.K24": sel.txa_qty,
                "Panel Code": sel.panel_code,
                "Reason": " / ".join(sel.messages),
            }
        )
    return rows


def write_excel_output(path: Path, selections: list[DdcSelection]) -> None:
    if Workbook is None:
        raise RuntimeError("openpyxl is required for Excel output")
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "DDC Selection"
    write_table(ws, summary_rows(selections))

    rules = wb.create_sheet("Rules")
    rules_rows = [
        {"Item": "Point total", "Rule": "Total = DI + DO + AI + AO"},
        {"Item": "PXC5.E24", "Rule": f"Selected when Total <= {PXC5_E24_MAX_POINTS}"},
        {
            "Item": "PXC7.E400S",
            "Rule": f"Selected when {PXC5_E24_MAX_POINTS} < Total <= {PXC7_E400S_MAX_POINTS}",
        },
        {"Item": "TXM1.16D", "Rule": "ceil(DI / 16)"},
        {"Item": "TXM1.6R", "Rule": "ceil(DO / 6)"},
        {"Item": "TXM1.8U/TXM1.8X", "Rule": "ceil((AI + AO) / 8), selected by analog module option"},
        {"Item": "TXS1.12F10", "Rule": "1 set per DDC panel"},
        {"Item": "TXA1.K24", "Rule": "1 set per DDC panel"},
    ]
    write_table(rules, rules_rows)

    wb.save(path)


def write_input_template(path: Path) -> None:
    if Workbook is None:
        raise RuntimeError("openpyxl is required for Excel template output")
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Input"
    rows = [
        {
            "DDC-No": "DDC-1",
            "Area": "Mechanical room",
            "Equipment": "AHU-1",
            "DI": 0,
            "DO": 0,
            "AI": 0,
            "AO": 0,
            "Panel_Size": "",
            "Analog_Module": "",
            "Controller_Override": "",
        },
        {
            "DDC-No": "DDC-2",
            "Area": "Mechanical room",
            "Equipment": "Pump system",
            "DI": 0,
            "DO": 0,
            "AI": 0,
            "AO": 0,
            "Panel_Size": "",
            "Analog_Module": "",
            "Controller_Override": "",
        },
    ]
    write_table(ws, rows)

    note = wb.create_sheet("Notes")
    note_rows = [
        {"Column": "DDC-No", "Required": "Yes", "Note": "DDC identifier"},
        {"Column": "DI", "Required": "Yes", "Note": "Digital input point count"},
        {"Column": "DO", "Required": "Yes", "Note": "Digital output point count"},
        {"Column": "AI", "Required": "Yes", "Note": "Analog input point count"},
        {"Column": "AO", "Required": "Yes", "Note": "Analog output point count"},
        {"Column": "Panel_Size", "Required": "No", "Note": "Example: 900x1800x300"},
        {"Column": "Analog_Module", "Required": "No", "Note": "Blank uses CLI default. Use TXM1.8U or TXM1.8X."},
        {"Column": "Controller_Override", "Required": "No", "Note": "Use only when manual controller selection is needed."},
    ]
    write_table(note, note_rows)
    wb.save(path)


def write_table(ws: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    style_worksheet(ws)


def style_worksheet(ws: Any) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    thin = Side(style="thin", color="D9E1E8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row in ws.iter_rows():
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if cell.row == 1:
                cell.fill = header_fill
                cell.font = header_font
    for col_cells in ws.columns:
        width = max(len(str(c.value or "")) for c in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(width + 2, 12), 60)
    ws.freeze_panes = "A2"


def run(input_path: Path, output_path: Path, default_analog_module: str) -> None:
    inputs = read_inputs(input_path)
    if not inputs:
        raise ValueError("No DDC rows found in input")
    selections = [select_ddc(ddc, default_analog_module) for ddc in inputs]
    if output_path.suffix.lower() == ".csv":
        write_csv_output(output_path, selections)
    else:
        write_excel_output(output_path, selections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple DDC material selector")
    parser.add_argument("--input", type=Path, help="Input .csv/.xlsx with DDC-No, DI, DO, AI, AO")
    parser.add_argument("--output", type=Path, help="Output .xlsx or .csv")
    parser.add_argument("--make-template", type=Path, help="Create an Excel input template and exit")
    parser.add_argument(
        "--analog-module",
        default="TXM1.8U",
        help="Default analog module: TXM1.8U or TXM1.8X. Optional per-row column: Analog_Module",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.make_template:
        write_input_template(args.make_template)
        print(f"created={args.make_template}")
        return
    if not args.input or not args.output:
        raise SystemExit("--input and --output are required unless --make-template is used")
    run(args.input, args.output, args.analog_module)
    print(f"created={args.output}")


if __name__ == "__main__":
    main()
