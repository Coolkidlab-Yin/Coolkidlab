# Architecture and physics

## Recommended components

```text
Program
├── single-instance mutex
├── argument parsing and self-tests
├── asset catalog
└── WPF application
    ├── transparent PetWindow
    ├── idle head/body/eye layers
    ├── pose or frame layer
    ├── state machine
    ├── high-resolution animation clock
    ├── BallWindow or in-window ball layer
    ├── settings persistence
    └── system tray and error log
```

Use a transparent, borderless WPF window with no taskbar entry. Keep hit testing available across the intended drag surface.

## State machine

Recommended states:

```text
Idle
Dragging
Walking
Running
Sitting
Jumping
Sleeping
Cuddling
FetchWindup
FetchFlight
FetchLanding
FetchChase
FetchPickup
FetchReturn
FetchDrop
```

Reject conflicting actions while dragging or fetching. Close child ball windows during shutdown and error recovery.

## Frame timing

Use `Stopwatch`, `CompositionTarget.Rendering`, or a render-priority timer. Compute:

```text
deltaTime = currentTimestamp - previousTimestamp
deltaTime = clamp(deltaTime, minimumStep, maximumStep)
```

Never encode speed as pixels per frame.

## Steering

```text
toTarget = target - position
distance = length(toTarget)
direction = normalize(toTarget)
desiredSpeed = maxSpeed * arrivalCurve(distance / arrivalRadius)
desiredVelocity = direction * desiredSpeed
velocity = approach(velocity, desiredVelocity, acceleration * deltaTime)
position += velocity * deltaTime
```

Use a slower return speed when carrying a ball. Update the facing sign from actual horizontal velocity. Inspect the source image to determine which sign means left or right.

## Gait

Advance phase from speed:

```text
speedRatio = clamp(speed / maxSpeed, 0, 1)
strideFrequency = idleFrequency + speedRatio * frequencyRange
stridePhase += strideFrequency * deltaTime
```

Select frames from normalized phase. Blend or transform between frames only after anchors are aligned.

## Ball flight

With screen Y increasing downward:

```text
x(t) = startX + velocityX * t
y(t) = startY + velocityY * t + 0.5 * gravity * t²
```

To land at a chosen target after duration `T`:

```text
velocityX = (targetX - startX) / T
velocityY = (targetY - startY - 0.5 * gravity * T²) / T
```

After impact, reduce vertical velocity by restitution and horizontal velocity by friction. Stop when bounce height and speed fall below visible thresholds.

During pickup, interpolate the ball from its resting point to the mouth anchor with an ease-in-out curve. During return, update the ball from the mouth anchor every frame. During drop, use a short gravity fall and close the ball only after ground contact.

## Head and eyes

Put head art and eye overlays under equivalent transforms. Use a neck pivot for rotation.

```text
headAngle += (targetAngle - headAngle) * smoothing
headX += (targetX - headX) * smoothing
headY += (targetY - headY) * smoothing
```

Clamp angle and pupil travel. Reset transforms when leaving or entering idle.

## Windows security

Prefer a PowerShell `Add-Type` launcher for unsigned local projects. Provide a signed executable for public binary distribution.

Do not instruct users to disable Smart App Control or antivirus protections.
