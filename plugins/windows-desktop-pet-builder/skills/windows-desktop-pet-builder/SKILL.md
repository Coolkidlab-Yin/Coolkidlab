---
name: windows-desktop-pet-builder
description: Build, customize, debug, or package an interactive Windows desktop pet from user-owned photos. Use when an AI coding agent needs to create a transparent C#/WPF desktop companion, generate or validate consistent sprite poses, implement drag and mouse-gaze behavior, add frame-rate-independent movement and fetch-ball physics, repair eye-mask or animation artifacts, or guide a user through a complete desktop-pet project.
---

# Windows Desktop Pet Builder

Build a working Windows desktop companion from approved photos and transparent sprites. Complete the implementation and validation instead of stopping at a mockup.

## 定位：提供判斷框架與引導邊界，不代替執行 Agent

這是引導型 skill：給規格、判斷框架與驗收標準，實作由執行 Agent 依使用者的照片與環境補完；不綁定特定 Agent（Codex、Claude Code 皆可用）。以下繁中六節是使用契約總覽，細節以後面的英文本體與 `references/` 為準。

## 開始前的輸入與執行契約

角色名、來源照片資料夾（唯讀）、視覺風格、輸出資料夾、照片使用權確認——完整清單見下方 Required inputs。只問無法安全推得的輸入。

## 預期產出

可實跑的 WPF 桌寵專案（拖曳、看滑鼠、撿球物理）、動畫貼圖資產、測試結果，以及專案／啟動器／輸出／log 的絕對路徑——見 Workflow 第 7 步。

## 完成定義與驗收

`--self-test`、`--render-test`、`--fetch-test` 全過，再實際啟動視窗確認行程存活無視覺瑕疵；判準見 `references/validation.md`。沒跑驗收不算完成。

## 限制、安全與隱私紅線

來源照片唯讀；照片、秘密、個人路徑不入版控；不關 Smart App Control 或防毒；`.ps1` 一律 UTF-8 with BOM——完整規則見 Non-negotiable rules。

## 來源與時效

規格以 `references/` 三份文件為準；內容基準 2026-08 主線版（含瀏覽器生圖工作流與 ZIP 下載的 MOTW 提醒），不依賴任何 image API 或金鑰。

## Required inputs

Resolve these before generating assets:

- Pet or character name.
- Absolute source-photo folder.
- Visual style, defaulting to semi-realistic 2.5D.
- Absolute project output folder.
- Confirmation that the user owns or may use the source images.

Ask only for inputs that cannot be discovered safely. Treat the source-photo folder as read-only.

## Non-negotiable rules

- Never commit source photos, secrets, personal paths, or authentication data.
- Never disable Smart App Control, antivirus, or Windows security controls.
- Use UTF-8 with BOM for `.ps1` and `.psm1` files.
- Use `deltaTime` for velocity, acceleration, gravity, and damping.
- Inspect the actual sprite direction; never infer facing from its filename.
- Keep eye overlays in the same transform hierarchy as the head.
- Avoid solid white blink masks over a photographic eye.
- Verify the running window, not only compilation.

## Workflow

### 1. Inspect the environment

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File `
  "<skill-folder>\scripts\check-prerequisites.ps1" `
  -PhotoFolder "<photo-folder>"
```

If the user has a local resource library, inspect it before downloading or recreating tools. Do not execute unknown installers. Use official sources for missing prerequisites.

### 2. Initialize a private project

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File `
  "<skill-folder>\scripts\new-desktop-pet-project.ps1" `
  -ProjectPath "<output-folder>" `
  -PetName "<pet-name>"
```

Preserve existing files. Stop if the target folder is non-empty unless the user explicitly requests integration.

### 3. Establish visual identity

Read [asset-spec.md](references/asset-spec.md).

Inventory the photo angles and extract identity constraints: face shape, eye spacing, nose, ears, coat pattern, body proportions, tail, and paws.

Generate a front-and-side identity sheet first. Request visual approval before producing the full pose set.

**This skill needs no image API and no API key.** The default path is to write
the prompts and have the user run them in ChatGPT's browser image generation,
then bring the images back. Ask for several angles of the same pose *inside one
image* rather than one request per pose — independent generations drift on
muzzle length, eye spacing, and markings, which is exactly what makes a pet
look blurry and stitched together. asset-spec.md carries the prompt templates
and the reject criteria; use them verbatim rather than improvising prompts.

### 4. Produce animation-ready sprites

Cut the approved sheets into frames. Create transparent, consistently anchored PNGs. Prefer:

- Separate idle head and body.
- At least four walk frames.
- At least six run frames.
- Distinct crouch, airborne, landing, pickup, carry, and drop poses.

Validate alpha edges and contact points. Do not accept a single translated side image as a run cycle.

### 5. Implement the Windows shell

Read [architecture-and-physics.md](references/architecture-and-physics.md).

Default to C# and WPF for a dependency-light Windows build. Implement:

- Transparent, borderless, optional topmost window.
- Drag handling with click-versus-drag threshold.
- Mouse gaze with smoothed head and pupil targets.
- Single-click, double-click, and context-menu actions.
- Configurable scale and autonomous-action interval.
- System tray, settings persistence, single-instance mutex, and error log.
- PowerShell source launcher as the safe default.

Use a state machine. Prevent long actions from re-entering fetch, drag, or jump states.

### 6. Implement animation and physics

Use a high-resolution clock and cap extreme frame gaps.

For movement:

```text
velocity = approach(velocity, desiredVelocity, acceleration * deltaTime)
position += velocity * deltaTime
```

Drive gait phase from real speed. Add acceleration, arrival deceleration, grounded contact, and correct sprite mirroring.

Split fetch into:

```text
windup → flight → damped landing → chase → pickup → carried return → drop
```

Use gravity for ball flight and drop. Keep the ball attached to a defined mouth anchor during return.

### 7. Validate and hand off

Read [validation.md](references/validation.md).

Implement and run:

- `--self-test`
- `--render-test`
- `--fetch-test`

Inspect left and right gaze renders for artifacts. Launch the normal application and verify its process remains responsive.

Return:

- Features completed.
- Commands and measured test results.
- Absolute project, launcher, output, and log paths.
- Any visual decision still awaiting approval.

## Bundled resources

- `scripts/check-prerequisites.ps1`: verify Windows, WPF compiler components, Git, and source photos.
- `scripts/new-desktop-pet-project.ps1`: create a privacy-safe starter directory.
- `references/asset-spec.md`: photo and sprite requirements.
- `references/architecture-and-physics.md`: implementation architecture and formulas.
- `references/validation.md`: automated and visual acceptance criteria.
- `assets/project-brief-template.md`: project brief copied by the scaffold script.
