# System Overview: Box Filling and Sealing Line

## Description

This PLC project controls an automated packaging line that fills boxes with product and seals them. The line consists of three stations connected by a conveyor:

1. **Infeed Station** – Empty boxes enter the line and are detected by a sensor
2. **Fill Station** – Boxes stop under a dispenser that fills them with product
3. **Seal Station** – Filled boxes are sealed with tape

## Physical Layout

```
[Empty Boxes] → [Infeed Sensor] → [Conveyor] → [Fill Station] → [Conveyor] → [Seal Station] → [Exit]
                     ↑                              ↑                              ↑
                PhotoEye_Infeed              PhotoEye_Fill                  PhotoEye_Seal
```

## Operation Modes

- **Automatic Mode**: Line runs continuously, processing boxes as they arrive
- **Manual Mode**: Operator controls each station individually via HMI buttons
- **Stopped**: Line is idle, all outputs off

## Safety

- Emergency stop button immediately halts all motion and outputs
- Safety gate sensor stops the line if the enclosure is opened
- Faults must be acknowledged before restarting

## Production Tracking

The system counts:
- Total boxes processed (since last reset)
- Boxes filled this shift
- Rejected boxes (fill timeout or seal failure)

## Cycle Overview

1. Box detected at infeed
2. Conveyor runs until box reaches fill station
3. Conveyor stops, fill valve opens
4. Fill continues until level sensor confirms full (or timeout)
5. Conveyor runs until box reaches seal station
6. Conveyor stops, seal cylinder extends and holds for seal time
7. Seal cylinder retracts, conveyor runs to exit box
8. Cycle repeats

## Key Timers

- Fill timeout: 5 seconds max
- Seal dwell time: 2 seconds
- Conveyor startup delay: 0.5 seconds after station complete
