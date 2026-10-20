(function () {
  "use strict";

  const LIMITS = {
    pxc4: 40,
    pxc5: 80,
    pxc7s: 100,
    pxc7m: 250,
  };

  const els = {};

  function setup() {
    [
      "projectName",
      "defaultAnalogModule",
      "addRowBtn",
      "exportCsvBtn",
      "ddcRows",
      "selectionRows",
      "summaryCount",
      "summaryPoints",
      "rowTemplate",
    ].forEach((id) => {
      els[id] = document.getElementById(id);
    });

    els.addRowBtn.addEventListener("click", () => addRow());
    els.exportCsvBtn.addEventListener("click", exportCsv);
    els.defaultAnalogModule.addEventListener("change", render);
    els.projectName.addEventListener("input", render);

    addRow({ ddcNo: "DDC-1" });
    render();
  }

  function addRow(data = {}) {
    const fragment = els.rowTemplate.content.cloneNode(true);
    const row = fragment.querySelector("tr");
    setValue(row, ".ddc-no", data.ddcNo || nextDdcNo());
    setValue(row, ".area", data.area || "");
    setValue(row, ".equipment", data.equipment || "");
    setValue(row, ".di", data.di || 0);
    setValue(row, ".do", data.do || 0);
    setValue(row, ".ai", data.ai || 0);
    setValue(row, ".ao", data.ao || 0);
    setValue(row, ".analog", data.analog || "");
    setValue(row, ".panel", data.panel || "");
    setValue(row, ".controller", data.controller || "");
    row.addEventListener("input", render);
    row.addEventListener("change", render);
    row.querySelector(".remove-row").addEventListener("click", () => {
      row.remove();
      if (!els.ddcRows.querySelector("tr")) {
        addRow();
      }
      render();
    });
    els.ddcRows.appendChild(fragment);
    render();
  }

  function setValue(row, selector, value) {
    row.querySelector(selector).value = value;
  }

  function nextDdcNo() {
    return `DDC-${els.ddcRows.querySelectorAll("tr").length + 1}`;
  }

  function readRows() {
    return Array.from(els.ddcRows.querySelectorAll("tr")).map((row) => {
      const data = {
        ddcNo: value(row, ".ddc-no") || "DDC",
        area: value(row, ".area"),
        equipment: value(row, ".equipment"),
        di: numberValue(row, ".di"),
        do: numberValue(row, ".do"),
        ai: numberValue(row, ".ai"),
        ao: numberValue(row, ".ao"),
        analog: value(row, ".analog") || els.defaultAnalogModule.value,
        panel: value(row, ".panel"),
        controllerOverride: value(row, ".controller"),
      };
      data.total = data.di + data.do + data.ai + data.ao;
      row.querySelector(".total-cell").textContent = formatNumber(data.total);
      return data;
    });
  }

  function value(row, selector) {
    return row.querySelector(selector).value.trim();
  }

  function numberValue(row, selector) {
    const parsed = Number(row.querySelector(selector).value);
    return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 0;
  }

  function ceilDiv(value, divisor) {
    return value <= 0 ? 0 : Math.ceil(value / divisor);
  }

  function selectController(row) {
    if (row.total <= 0) {
      return {
        controller: "N/A",
        reason: "관제점을 입력하면 자동 선정",
      };
    }
    if (row.controllerOverride) {
      return {
        controller: row.controllerOverride,
        reason: `수동 지정: ${row.controllerOverride}`,
      };
    }
    if (row.total <= LIMITS.pxc4) {
      return {
        controller: "PXC4.E16S-2",
        reason: `Total ${row.total} <= ${LIMITS.pxc4}, 소형 DDC 후보`,
      };
    }
    if (row.total <= LIMITS.pxc5) {
      return {
        controller: "PXC5.E24",
        reason: `Total ${row.total} <= ${LIMITS.pxc5}, PXC5.E24 선정`,
      };
    }
    if (row.total <= LIMITS.pxc7s) {
      return {
        controller: "PXC7.E400S",
        reason: `Total ${row.total} > ${LIMITS.pxc5}, PXC7.E400S 선정`,
      };
    }
    if (row.total <= LIMITS.pxc7m) {
      return {
        controller: "PXC7.E400M",
        reason: `Total ${row.total} > ${LIMITS.pxc7s}, PXC7.E400M 선정`,
      };
    }
    return {
      controller: "PXC7.E400L",
      reason: `Total ${row.total} > ${LIMITS.pxc7m}, 대형 구성 검토 필요`,
    };
  }

  function selectPanel(row, selection) {
    if (row.panel) {
      return row.panel;
    }
    if (selection.controller === "PXC7.E400S" || selection.controller === "PXC7.E400M" || row.total > LIMITS.pxc5) {
      return "E";
    }
    if (row.total > LIMITS.pxc4) {
      return "D";
    }
    if (row.total > 20) {
      return "C";
    }
    return "B";
  }

  function calculateSelection(row) {
    const picked = selectController(row);
    const analogModule = row.analog === "TXM1.8U" ? "TXM1.8U" : "TXM1.8X";
    const selection = {
      ...row,
      controller: picked.controller,
      controllerReason: picked.reason,
      txm16d: ceilDiv(row.di, 16),
      txm6r: ceilDiv(row.do, 6),
      txm8u: analogModule === "TXM1.8U" ? ceilDiv(row.ai + row.ao, 8) : 0,
      txm8x: analogModule === "TXM1.8X" ? ceilDiv(row.ai + row.ao, 8) : 0,
      txs: row.total > 0 ? 1 : 0,
      txa: row.total > 0 ? 1 : 0,
      analogModule,
    };
    selection.panel = selectPanel(row, selection);
    selection.reason = `${picked.reason}. ${analogModule} = ceil((AI+AO)/8).`;
    return selection;
  }

  function render() {
    const rows = readRows();
    const selections = rows.map(calculateSelection);
    renderSelections(selections);
    els.summaryCount.textContent = formatNumber(selections.length);
    els.summaryPoints.textContent = formatNumber(rows.reduce((sum, row) => sum + row.total, 0));
  }

  function renderSelections(selections) {
    els.selectionRows.innerHTML = "";
    selections.forEach((sel) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(sel.ddcNo)}</td>
        <td class="number-cell">${formatNumber(sel.total)}</td>
        <td><span class="controller-pill ${controllerClass(sel.controller)}">${escapeHtml(sel.controller)}</span></td>
        <td class="number-cell">${formatNumber(sel.txm16d)}</td>
        <td class="number-cell">${formatNumber(sel.txm6r)}</td>
        <td class="number-cell">${formatNumber(sel.txm8u)}</td>
        <td class="number-cell">${formatNumber(sel.txm8x)}</td>
        <td class="number-cell">${formatNumber(sel.txs)}</td>
        <td class="number-cell">${formatNumber(sel.txa)}</td>
        <td class="reason-cell">${escapeHtml(sel.reason)}</td>
      `;
      els.selectionRows.appendChild(tr);
    });
  }

  function controllerClass(controller) {
    if (controller === "PXC7.E400M" || controller === "PXC7.E400L") {
      return "danger";
    }
    if (controller === "PXC7.E400S") {
      return "warn";
    }
    return "";
  }

  function exportCsv() {
    const selections = readRows().map(calculateSelection);
    const rows = [
      ["Project", els.projectName.value],
      [],
      ["DDC-No", "DI", "DO", "AI", "AO", "Total", "Controller", "TXM1.16D", "TXM1.6R", "TXM1.8U", "TXM1.8X", "TXS1.12F10", "TXA1.K24", "Panel", "Reason"],
      ...selections.map((sel) => [
        sel.ddcNo,
        sel.di,
        sel.do,
        sel.ai,
        sel.ao,
        sel.total,
        sel.controller,
        sel.txm16d,
        sel.txm6r,
        sel.txm8u,
        sel.txm8x,
        sel.txs,
        sel.txa,
        sel.panel,
        sel.reason,
      ]),
    ];
    downloadCsv(rows, "ddc_selection_result.csv");
  }

  function downloadCsv(rows, filename) {
    const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  }

  function csvCell(value) {
    const text = String(value ?? "");
    return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("ko-KR");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  window.DdcCalculator = {
    calculateSelection,
    LIMITS,
  };

  document.addEventListener("DOMContentLoaded", setup);
})();
