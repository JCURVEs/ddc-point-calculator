# DDC Selector

DI, DO, AI, AO 관제점 수로 DDC 컨트롤러 후보와 TX-I/O 모듈 수량을 계산하는 웹앱입니다. 여러 DDC를 한 화면에서 비교하고, 선정 결과를 CSV로 내려받을 수 있습니다.

**바로 사용:** [GitHub Pages 웹 계산기](https://jcurves.github.io/ddc-selector-v1/) · [Hugging Face Space](https://huggingface.co/spaces/Jcurve/ddc-selector-v1)

이 저장소는 계산기 소스와 Excel 입력/출력용 Python CLI를 포함합니다.

## 사용 방법

1. 웹 계산기에서 프로젝트명을 입력합니다.
2. DDC 행을 추가하고 각 행에 DI, DO, AI, AO 수량을 입력합니다.
3. 아날로그 신호에 맞춰 `TXM1.8U` 또는 `TXM1.8X`를 선택합니다.
4. 자동 선정 결과를 확인하고, 현장 기준이 있으면 컨트롤러나 판넬을 수동 지정합니다.
5. `CSV 내보내기`로 선정 결과를 저장합니다.

웹앱은 [webapp/index.html](webapp/index.html)을 로컬 브라우저에서 열어 사용할 수도 있습니다. 입력한 프로젝트명과 관제점은 서버로 전송하지 않습니다.

## 계산 범위

총 관제점은 `DI + DO + AI + AO`입니다. 별도 지정이 없으면 다음 기준으로 컨트롤러 후보를 표시합니다.

| 총 관제점 | 자동 선정 후보 |
| ---: | --- |
| 0-40 | `PXC4.E16S-2` |
| 41-80 | `PXC5.E24` |
| 81-100 | `PXC7.E400S` |
| 101-250 | `PXC7.E400M` |
| 251 이상 | `PXC7.E400L` 검토 |

| 자재 | 수량 계산 |
| --- | --- |
| `TXM1.16D` | `ceil(DI / 16)` |
| `TXM1.6R` | `ceil(DO / 6)` |
| `TXM1.8U` 또는 `TXM1.8X` | `ceil((AI + AO) / 8)` |
| `TXS1.12F10`, `TXA1.K24` | DDC당 각 1개 |

예를 들어 `DI 16 / DO 8 / AI 16 / AO 7`이면 총 47포인트로 계산합니다. 자동 후보는 `PXC5.E24`, 모듈 수량은 `TXM1.16D` 1개, `TXM1.6R` 2개, 선택한 아날로그 모듈 3개입니다.

## Excel CLI

Python 3과 `openpyxl`이 필요합니다.

```bash
pip install openpyxl
python ddc_selector.py --make-template inputs/ddc_input_template.xlsx
python ddc_selector.py --input inputs/ddc_input_template.xlsx --output outputs/ddc_selection.xlsx --analog-module TXM1.8X
```

결과 파일에는 `DDC Selection`, `Rules` 시트가 생성됩니다.

## 검증

```bash
python -m unittest test_ddc_selector.py
node --check webapp/app.js
```

## 적용 전 확인

이 도구는 관제점 수를 기준으로 한 **초기 선정용**입니다. 내장 I/O 차감, 통신 연동 포인트, 여유 포인트, 신호별 전기적 사양, TX-I/O 전원 용량 및 판넬 실장 가능 여부는 자동 검증하지 않습니다. 최종 모델과 품번은 현장 사양서와 최신 제품 자료로 확인해야 합니다.

## 라이선스

저작권은 [LICENSE](LICENSE)에 명시되어 있습니다.
