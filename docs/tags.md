# PLC Tags

## Inputs

| Tag Name | Type | Description |
|----------|------|-------------|
| PhotoEye_Infeed | BOOL | Photoeye sensor at infeed station. TRUE when box is present. |
| PhotoEye_Fill | BOOL | Photoeye sensor at fill station. TRUE when box is present. |
| PhotoEye_Seal | BOOL | Photoeye sensor at seal station. TRUE when box is present. |
| Level_Sensor | BOOL | Sensor inside fill dispenser. TRUE when box is full. |
| Seal_Cylinder_Home | BOOL | Proximity sensor. TRUE when seal cylinder is fully retracted. |
| Seal_Cylinder_Extended | BOOL | Proximity sensor. TRUE when seal cylinder is fully extended. |
| EmergencyStop | BOOL | E-stop button. TRUE when pressed (NC contact, so TRUE = stopped). |
| Safety_Gate_Closed | BOOL | Safety interlock. TRUE when guard door is closed. |
| HMI_Start_Button | BOOL | Operator start button from HMI. Momentary TRUE on press. |
| HMI_Stop_Button | BOOL | Operator stop button from HMI. Momentary TRUE on press. |
| HMI_Reset_Button | BOOL | Fault reset button from HMI. Momentary TRUE on press. |
| HMI_Manual_Mode | BOOL | Mode selector. TRUE = Manual mode, FALSE = Auto mode. |
| HMI_Manual_Conveyor | BOOL | Manual jog button for conveyor. TRUE while held. |
| HMI_Manual_Fill | BOOL | Manual trigger for fill valve. TRUE while held. |
| HMI_Manual_Seal | BOOL | Manual trigger for seal cylinder. TRUE while held. |

## Outputs

| Tag Name | Type | Description |
|----------|------|-------------|
| Conveyor_Run | BOOL | Conveyor motor contactor. TRUE = conveyor running. |
| Fill_Valve | BOOL | Solenoid valve for product dispenser. TRUE = dispensing product. |
| Seal_Cylinder_Extend | BOOL | Solenoid to extend seal cylinder. TRUE = extending/holding. |
| Stack_Light_Green | BOOL | Stack light green lamp. TRUE = running normally. |
| Stack_Light_Yellow | BOOL | Stack light yellow lamp. TRUE = stopped or manual mode. |
| Stack_Light_Red | BOOL | Stack light red lamp. TRUE = faulted. |
| HMI_Fault_Indicator | BOOL | Fault indicator on HMI screen. TRUE = fault active. |

## Internal State

| Tag Name | Type | Description |
|----------|------|-------------|
| Line_Running | BOOL | Internal flag. TRUE when line is in auto and running. |
| Fault_Active | BOOL | TRUE when any fault condition is present. |
| Fault_Code | INT | Current fault code. 0 = no fault. See fault codes below. |
| Fill_In_Progress | BOOL | TRUE while fill station is actively filling a box. |
| Seal_In_Progress | BOOL | TRUE while seal station is actively sealing a box. |
| Box_At_Fill | BOOL | Latched flag. TRUE when a box is present and waiting/filling at fill station. |
| Box_At_Seal | BOOL | Latched flag. TRUE when a box is present and waiting/sealing at seal station. |

## Timers

| Tag Name | Type | Description |
|----------|------|-------------|
| Fill_Timer | TIMER | Times the fill operation. PRE = 5000ms (5 second timeout). |
| Seal_Timer | TIMER | Times the seal dwell. PRE = 2000ms (2 second hold). |
| Conveyor_Delay_Timer | TIMER | Delay before conveyor starts after station complete. PRE = 500ms. |

## Counters

| Tag Name | Type | Description |
|----------|------|-------------|
| Total_Box_Count | DINT | Total boxes that have exited the line since last reset. |
| Shift_Box_Count | DINT | Boxes processed this shift. Reset by operator. |
| Rejected_Box_Count | DINT | Boxes rejected due to fill timeout or seal failure. |

## Fault Codes

| Fault_Code Value | Meaning |
|------------------|---------|
| 0 | No fault |
| 1 | Emergency stop pressed |
| 2 | Safety gate opened |
| 3 | Fill timeout (box not full within 5 seconds) |
| 4 | Seal timeout (cylinder did not extend within 3 seconds) |
| 5 | Seal cylinder did not retract within 3 seconds |
