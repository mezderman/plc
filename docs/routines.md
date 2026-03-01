# PLC Routines

## MainRoutine

**Description:** This is the main program routine that runs every PLC scan. It handles safety checks, mode selection, and calls the appropriate subroutines.

**Called By:** PLC operating system (continuous scan)

**Calls:** SafetyCheck, AutoMode, ManualMode, FaultHandler, StackLightControl

```
// Safety is always checked first, regardless of mode
Call SafetyCheck

// If faulted, only run fault handler and stack lights
IF Fault_Active THEN
    Call FaultHandler
    Call StackLightControl
    RETURN
END IF

// Mode selection
IF HMI_Manual_Mode THEN
    Line_Running := FALSE
    Call ManualMode
ELSE
    Call AutoMode
END IF

Call StackLightControl
```

---

## SafetyCheck

**Description:** Monitors safety devices and triggers faults if safety conditions are violated. Also handles fault reset requests.

**Called By:** MainRoutine

```
// Emergency stop check (NC contact, so TRUE means pressed/stopped)
IF EmergencyStop THEN
    Fault_Active := TRUE
    Fault_Code := 1
    // Immediately kill all outputs
    Conveyor_Run := FALSE
    Fill_Valve := FALSE
    Seal_Cylinder_Extend := FALSE
END IF

// Safety gate check
IF NOT Safety_Gate_Closed THEN
    Fault_Active := TRUE
    Fault_Code := 2
    // Stop all outputs
    Conveyor_Run := FALSE
    Fill_Valve := FALSE
    Seal_Cylinder_Extend := FALSE
END IF

// Fault reset logic
IF HMI_Reset_Button AND Fault_Active THEN
    // Only allow reset if safety conditions are now OK
    IF NOT EmergencyStop AND Safety_Gate_Closed THEN
        Fault_Active := FALSE
        Fault_Code := 0
        Fill_Timer.Reset()
        Seal_Timer.Reset()
    END IF
END IF
```

---

## AutoMode

**Description:** Controls automatic operation of the packaging line. Manages the conveyor, fill station, and seal station based on sensor inputs.

**Called By:** MainRoutine (when not in manual mode and not faulted)

```
// Start/Stop control
IF HMI_Start_Button AND NOT Line_Running THEN
    Line_Running := TRUE
END IF

IF HMI_Stop_Button AND Line_Running THEN
    Line_Running := FALSE
END IF

// If line not running, ensure outputs are off and exit
IF NOT Line_Running THEN
    Conveyor_Run := FALSE
    Fill_Valve := FALSE
    // Don't force seal cylinder off if mid-cycle (safety)
    IF NOT Seal_In_Progress THEN
        Seal_Cylinder_Extend := FALSE
    END IF
    RETURN
END IF

// === FILL STATION LOGIC ===

// Detect box arriving at fill station
IF PhotoEye_Fill AND NOT Box_At_Fill AND NOT Fill_In_Progress THEN
    Box_At_Fill := TRUE
END IF

// Fill sequence
IF Box_At_Fill THEN
    // Stop conveyor for filling
    // (but only if seal station isn't also needing the conveyor stopped)
    
    // Start filling if not already
    IF NOT Fill_In_Progress THEN
        Fill_In_Progress := TRUE
        Fill_Timer.Start()
    END IF
    
    // Filling in progress
    IF Fill_In_Progress THEN
        Fill_Valve := TRUE
        
        // Check for fill complete (level sensor)
        IF Level_Sensor THEN
            Fill_Valve := FALSE
            Fill_In_Progress := FALSE
            Box_At_Fill := FALSE
            Fill_Timer.Reset()
            Conveyor_Delay_Timer.Start()
        END IF
        
        // Check for fill timeout
        IF Fill_Timer.DN THEN
            Fill_Valve := FALSE
            Fill_In_Progress := FALSE
            Box_At_Fill := FALSE
            Fault_Active := TRUE
            Fault_Code := 3
            Rejected_Box_Count := Rejected_Box_Count + 1
        END IF
    END IF
END IF

// === SEAL STATION LOGIC ===

// Detect box arriving at seal station
IF PhotoEye_Seal AND NOT Box_At_Seal AND NOT Seal_In_Progress THEN
    Box_At_Seal := TRUE
END IF

// Seal sequence
IF Box_At_Seal THEN
    // Start sealing if not already
    IF NOT Seal_In_Progress THEN
        Seal_In_Progress := TRUE
        Seal_Cylinder_Extend := TRUE
        Seal_Timer.Start()
    END IF
    
    // Wait for seal dwell time
    IF Seal_In_Progress AND Seal_Timer.DN THEN
        Seal_Cylinder_Extend := FALSE
        
        // Wait for cylinder to retract
        IF Seal_Cylinder_Home THEN
            Seal_In_Progress := FALSE
            Box_At_Seal := FALSE
            Seal_Timer.Reset()
            Total_Box_Count := Total_Box_Count + 1
            Shift_Box_Count := Shift_Box_Count + 1
            Conveyor_Delay_Timer.Start()
        END IF
    END IF
END IF

// === CONVEYOR LOGIC ===

// Conveyor runs if:
// 1. Line is running, AND
// 2. Not actively filling (box at fill station being filled), AND
// 3. Not actively sealing (box at seal station being sealed), AND
// 4. Conveyor delay timer is not running OR has completed

IF Line_Running 
   AND NOT Fill_In_Progress 
   AND NOT Seal_In_Progress 
   AND (NOT Conveyor_Delay_Timer.EN OR Conveyor_Delay_Timer.DN) THEN
    Conveyor_Run := TRUE
    IF Conveyor_Delay_Timer.DN THEN
        Conveyor_Delay_Timer.Reset()
    END IF
ELSE
    Conveyor_Run := FALSE
END IF
```

---

## ManualMode

**Description:** Allows operator to manually control individual stations via HMI buttons. Used for setup, maintenance, and troubleshooting.

**Called By:** MainRoutine (when in manual mode and not faulted)

```
// Manual conveyor jog
IF HMI_Manual_Conveyor THEN
    Conveyor_Run := TRUE
ELSE
    Conveyor_Run := FALSE
END IF

// Manual fill trigger
IF HMI_Manual_Fill THEN
    Fill_Valve := TRUE
ELSE
    Fill_Valve := FALSE
END IF

// Manual seal trigger
// Only allow if conveyor is stopped (safety)
IF HMI_Manual_Seal AND NOT Conveyor_Run THEN
    Seal_Cylinder_Extend := TRUE
ELSE
    Seal_Cylinder_Extend := FALSE
END IF
```

---

## FaultHandler

**Description:** Manages fault conditions and ensures outputs are in a safe state when faulted.

**Called By:** MainRoutine (when Fault_Active is TRUE)

```
// Ensure line is marked as not running
Line_Running := FALSE

// Keep fill valve closed
Fill_Valve := FALSE

// Conveyor stopped
Conveyor_Run := FALSE

// Seal cylinder - retract if extended (don't leave it hanging)
IF NOT Seal_Cylinder_Home THEN
    Seal_Cylinder_Extend := FALSE
END IF

// Set HMI fault indicator
HMI_Fault_Indicator := TRUE

// Clear fault indicator when fault clears
IF NOT Fault_Active THEN
    HMI_Fault_Indicator := FALSE
END IF
```

---

## StackLightControl

**Description:** Controls the stack light based on current machine state.

**Called By:** MainRoutine

```
// Red = Faulted
Stack_Light_Red := Fault_Active

// Yellow = Stopped or Manual Mode (but not faulted)
Stack_Light_Yellow := (NOT Line_Running OR HMI_Manual_Mode) AND NOT Fault_Active

// Green = Running in Auto
Stack_Light_Green := Line_Running AND NOT HMI_Manual_Mode AND NOT Fault_Active
```
