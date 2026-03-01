# Test Questions and Reference Answers

Use these questions to test your agent and evaluate LLM performance. Reference answers are provided for comparison, though reasonable paraphrasing is acceptable.

---

## Question 1 (Easy - Tag Lookup)
**Question:** What does the PhotoEye_Fill sensor do?

**Reference Answer:** PhotoEye_Fill is a photoeye sensor located at the fill station. It detects when a box is present at the fill station and outputs TRUE when a box is detected.

---

## Question 2 (Easy - Tag Lookup)
**Question:** What are all the fault codes and what do they mean?

**Reference Answer:** 
- Fault Code 0: No fault
- Fault Code 1: Emergency stop pressed
- Fault Code 2: Safety gate opened
- Fault Code 3: Fill timeout (box not full within 5 seconds)
- Fault Code 4: Seal timeout (cylinder did not extend within 3 seconds)
- Fault Code 5: Seal cylinder did not retract within 3 seconds

---

## Question 3 (Medium - Single Routine)
**Question:** What happens when the emergency stop is pressed?

**Reference Answer:** When the emergency stop is pressed (EmergencyStop becomes TRUE), the SafetyCheck routine immediately sets Fault_Active to TRUE and Fault_Code to 1. It then turns off all outputs: Conveyor_Run, Fill_Valve, and Seal_Cylinder_Extend are all set to FALSE. The line stops immediately and the red stack light turns on.

---

## Question 4 (Medium - Single Routine)
**Question:** How does the operator reset a fault?

**Reference Answer:** The operator presses the HMI_Reset_Button. The SafetyCheck routine checks if safety conditions are OK (EmergencyStop is not pressed AND Safety_Gate_Closed is TRUE). If both conditions are met, Fault_Active is set to FALSE, Fault_Code is set to 0, and the Fill_Timer and Seal_Timer are reset. If safety conditions are not OK (e.g., E-stop still pressed), the reset is ignored.

---

## Question 5 (Medium - System Understanding)
**Question:** What color is the stack light when the machine is in manual mode?

**Reference Answer:** Yellow. The StackLightControl routine sets Stack_Light_Yellow to TRUE when the line is in manual mode (HMI_Manual_Mode is TRUE) and not faulted. The green light is off because Line_Running is FALSE or manual mode is active.

---

## Question 6 (Medium - Process Flow)
**Question:** Walk me through what happens when a box arrives at the fill station.

**Reference Answer:** 
1. PhotoEye_Fill detects the box (becomes TRUE)
2. Box_At_Fill is latched TRUE
3. Fill_In_Progress is set TRUE and Fill_Timer starts
4. Conveyor_Run is set FALSE (conveyor stops)
5. Fill_Valve opens (set TRUE) and product dispenses
6. When Level_Sensor detects the box is full, Fill_Valve closes, Fill_In_Progress and Box_At_Fill are reset to FALSE, Fill_Timer resets, and Conveyor_Delay_Timer starts
7. After the 500ms conveyor delay, the conveyor restarts to move the box to the seal station

---

## Question 7 (Medium - Logic Understanding)
**Question:** Why can't you extend the seal cylinder manually while the conveyor is running?

**Reference Answer:** This is a safety interlock. In ManualMode, the seal cylinder extend command (Seal_Cylinder_Extend) is only allowed when the conveyor is stopped (NOT Conveyor_Run). This prevents the seal cylinder from extending while a box is moving, which could damage equipment or product, or create a safety hazard.

---

## Question 8 (Hard - Cross-Routine)
**Question:** What conditions must be true for the conveyor to run in automatic mode?

**Reference Answer:** All of the following must be true:
1. Line_Running must be TRUE (operator has pressed start and not stop)
2. Fill_In_Progress must be FALSE (not actively filling a box)
3. Seal_In_Progress must be FALSE (not actively sealing a box)
4. Conveyor_Delay_Timer must either not be running OR have completed (DN bit TRUE)
5. Implicitly: Fault_Active must be FALSE (otherwise AutoMode routine doesn't execute)

---

## Question 9 (Hard - Troubleshooting)
**Question:** The conveyor won't start even though the line is in auto mode and the operator pressed start. What should I check?

**Reference Answer:** Check the following:
1. Is there a fault active? Check Fault_Active and Fault_Code. If faulted, the line won't run. Common faults are E-stop pressed (code 1) or safety gate open (code 2).
2. Is Fill_In_Progress TRUE? If a box is being filled, the conveyor waits.
3. Is Seal_In_Progress TRUE? If a box is being sealed, the conveyor waits.
4. Is the Conveyor_Delay_Timer still running? There's a 500ms delay after fill or seal completes.
5. Did Line_Running actually latch TRUE? The start button is momentary, so check if Line_Running is TRUE.
6. Check HMI_Manual_Mode - if TRUE, the system is in manual mode and AutoMode doesn't run.

---

## Question 10 (Hard - Failure Scenario)
**Question:** What happens if a box is at the fill station but never gets full?

**Reference Answer:** The Fill_Timer runs for 5 seconds (5000ms preset). If Level_Sensor never becomes TRUE within that time, the timer's DN (done) bit activates. This triggers a fill timeout: Fill_Valve is closed, Fill_In_Progress and Box_At_Fill are reset to FALSE, Fault_Active is set TRUE with Fault_Code 3, and Rejected_Box_Count is incremented by 1. The line stops and the red stack light turns on. An operator must investigate, remove the box, and reset the fault to continue.

---

## Scoring Guidance

Up to you.

**Key evaluation criteria:**

Go wild.
