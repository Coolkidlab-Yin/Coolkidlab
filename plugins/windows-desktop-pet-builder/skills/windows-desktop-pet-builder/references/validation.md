# Validation checklist

## Automated tests

### Self-test

Validate:

- Required sprites exist.
- Images decode and have positive dimensions.
- Required settings are finite and within safe bounds.
- Output and log directories are writable.

Expected command:

```powershell
.\Start-DesktopPet.ps1 --self-test
```

Expected exit code: `0`.

### Render test

Render the visual tree to PNG after layout. Test:

- Center gaze.
- Far-left gaze.
- Far-right gaze.
- Debug background and transparent background.

Reject white eye masks, stale overlays, rectangular alpha artifacts, clipped ears, or detached pupils.

### Fetch test

Add a deterministic `--fetch-test` mode. Start fetch after load, close only after the ball is dropped, and use a timeout that returns a nonzero exit code.

Record:

- Total sequence duration.
- Successful traversal of all fetch states.
- Ball child window created and closed.
- Main process still responsive after the normal launch.

## Visual acceptance

- The face matches the approved identity sheet.
- The head pivot stays attached to the neck.
- Eye overlays rotate and translate with the head.
- Walking and running show actual leg-pose changes.
- The nose faces the movement direction.
- Start and stop use acceleration instead of instantaneous speed.
- The ball follows a parabola, bounces with decay, and remains at the mouth during return.
- The pet stays within the virtual desktop bounds.
- Scale changes do not clip the head or feet.

## Interaction acceptance

- Dragging does not accidentally trigger a click action.
- Single click and double click remain distinguishable.
- Context menu actions work while the window is topmost.
- Autonomy can be paused and resumes with a new schedule.
- Settings persist across a clean restart.
- Tray icon and child windows close on exit.

## Handoff evidence

Report exact commands, exit codes, measured durations, process ID, responsiveness, and absolute paths. Distinguish automated evidence from visual approval.
