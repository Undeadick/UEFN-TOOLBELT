# Развёртывание UEFN Toolbelt (универсальная инструкция)

Полный путь от чистой машины до «ИИ управляет UEFN»: клонирование, установка
в проект, подключение Claude Code, проверка. Англоязычная документация
проекта: `README.md`, `ARCHITECTURE.md`, `CLAUDE.md`.

---

## 0. Требования

| Что | Зачем |
|---|---|
| Fortnite + UEFN (Epic Games Launcher) | сам редактор |
| Python 3.10+ **вне** UEFN (`py -V`) | внешний MCP-сервер |
| `pip install mcp` | пакет FastMCP для mcp_server.py |
| Claude Code (или любой MCP-клиент) | ИИ-агент |
| git | клонирование и обновления |

UEFN несёт собственный Python 3.11 внутри — ставить туда ничего не нужно
(в редакторе доступны только stdlib + `unreal`).

## 1. Клонирование

```powershell
git clone https://github.com/Undeadick/UEFN-TOOLBELT.git
cd UEFN-TOOLBELT
# опционально, для Verse-инструментов (verse_book_search/chapter):
git clone https://github.com/verselang/book.git verse-book
```

База знаний по дизайну карт (`docs/design_book/`) уже в репозитории —
ничего дополнительно клонировать не нужно.

## 2. Установка в UEFN-проект

Репозиторий и UEFN-проект — **разные папки**. Toolbelt копируется в проект:

| Из репозитория | Куда в проект |
|---|---|
| `Content/Python/UEFN_Toolbelt/` (вся папка) | `<проект>/Content/Python/UEFN_Toolbelt/` |
| `init_unreal.py` (корень репо) | `<проект>/Content/Python/init_unreal.py` * |

\* если в проекте уже есть свой `init_unreal.py` — не перезаписывать,
а добавить из нашего только цикл обнаружения пакетов.

Способы:
- **`python install.py`** — интерактивный установщик (ищет проекты сам);
- **`deploy.bat`** — только если проекты лежат в стандартном
  `%USERPROFILE%\Documents\Fortnite Projects` (иначе скрипт промахнётся);
- **вручную / robocopy** — самый надёжный на нестандартных путях:

```powershell
robocopy "Content\Python\UEFN_Toolbelt" "D:\Projects\MyIsland\Content\Python\UEFN_Toolbelt" /MIR
Copy-Item init_unreal.py "D:\Projects\MyIsland\Content\Python\"
```

⚠️ UEFN сканирует `Content/Python` только при старте: после ПЕРВОЙ установки
в проект — полный перезапуск редактора.

## 3. Подключение Claude Code (MCP)

В рабочей папке Claude Code создать/дополнить `.mcp.json`:

```json
{
  "mcpServers": {
    "uefn-toolbelt": {
      "command": "C:/Path/To/python.exe",
      "args": ["C:/Path/To/UEFN-TOOLBELT/mcp_server.py"],
      "env": { "UEFN_MCP_PORT": "8765" }
    }
  }
}
```

- `command` — внешний Python (тот, куда ставился `pip install mcp`);
- `args` — абсолютный путь к `mcp_server.py` **в репозитории** (не в проекте);
- после правки `.mcp.json` — перезапустить Claude Code.

## 4. Запуск моста в UEFN

Открыть проект в UEFN → Output Log → переключить строку ввода на Python →
вставить:

```python
import sys; [sys.modules.pop(k) for k in list(sys.modules) if "UEFN_Toolbelt" in k]; import UEFN_Toolbelt as tb; tb.register_all_tools(); tb.run("mcp_start")
```

Ожидаемый вывод: `370 tools registered`, затем
`[MCP] ✓ Listener running on http://127.0.0.1:8765`.

Эту строку вводят после каждого запуска редактора (листенер живёт в сессии).

## 5. Проверка

Из Claude Code: инструмент `ping` сервера `uefn-toolbelt` → `status: ok`.
Изнутри UEFN: `tb.run("toolbelt_smoke_test")` → все слои зелёные.

## 6. Опциональные шаги

**Курированные палитры** (для `building_generate`):
```powershell
Copy-Item palettes\*.json "$env:LOCALAPPDATA\UnrealEditorFortnite\Saved\UEFN_Toolbelt\palettes\"
```

**Слабый GPU (≤ 8 ГБ VRAM)** — иначе скриншоты движком роняют редактор
(D3D12 out-of-memory):
- `%LOCALAPPDATA%\UnrealEditorFortnite\Saved\Config\WindowsEditor\EditorSettings.ini`
  → `[ScalabilityGroups]`: всё на 1, `sg.GlobalIlluminationQuality=0`,
  `sg.ReflectionQuality=0`, `sg.ResolutionQuality=67`;
- там же создать `Engine.ini`:
  ```ini
  [SystemSettings]
  r.Streaming.PoolSize=512
  r.Streaming.LimitPoolSizeToVRAM=1
  ```
- скриншоты — только внешним захватом: `scripts/capture_uefn_window.ps1`
  (движок не участвует вовсе). Править ini только при ЗАКРЫТОМ редакторе.

**Автосборка Verse**: `scripts/build_verse.ps1` (шлёт Ctrl+Shift+B окну
UEFN) + `tb.run("verse_build_status")` для результата.

**Скиллы Claude Code**: `.claude/skills/uefn-map-builder` и
`uefn-verse-loop` подхватываются автоматически, когда Claude Code работает
в папке репозитория; для другой рабочей папки скопировать их в её
`.claude/skills/`.

## 7. Цикл разработки (если правишь сам Toolbelt)

```
правка в репо
  → py scripts/drift_check.py                     (должен быть PASS)
  → robocopy Content\Python\UEFN_Toolbelt <проект>... /MIR
  → в UEFN: точечный reload модуля ИЛИ nuclear reload (см. CLAUDE.md)
  → живой тест → коммит
```

Жёсткие правила: новый модуль в `tools/__init__.py` = полный перезапуск
редактора (Quirk #26); `unreal.Rotator` — только именованные аргументы
(Quirk #35); перед постройкой карт — `docs/design_book/09_lessons.md`.

## 8. Типовые проблемы

| Симптом | Причина → решение |
|---|---|
| `Unknown tool` на любой вызов | не вызван `tb.register_all_tools()` после импорта |
| MCP-клиент: connection refused | листенер не запущен в UEFN (шаг 4) |
| `ModuleNotFoundError: UEFN_Toolbelt` | первая установка без перезапуска редактора |
| Ошибки валидации «недопустимые ссылки» | ассеты вне разрешённых неймспейсов — см. `docs/design_book/08_publishing.md` |
| Редактор падает на скриншоте | VRAM OOM — см. «Слабый GPU» выше |
| `tb` is not defined после смены проекта | Python-окружение сбросилось — повторить строку из шага 4 |
