

Excellent instinct to pause here. Let me think through the implications and ask some clarifying questions.

##   Questions About Bit Organization




  ## Q2. Do We Still Need sw_trigger_enable?
  No. Lets remove it now that we have debugged the metavalue issue.

  
##  Q3: Do we still need  hw_trigger_enable ?
  I.e.-  is there a scenario where you're armed but want to block hardware triggers?

Not that I cna think of -- that was really only relevant when debugging simulation vs hardware fidelity

  ## Q4: Is auto_rearm_enable Really a "Lifecycle" Control?
No. This should be moved into CR2-10. Good catch

 
  4. Bit Layout Options

  Here are two possible layouts:

  Option A: Functional Grouping
  CR0[31:29] = FORGE control
  CR0[7:6]   = Trigger source enables (hw_trigger_enable, sw_trigger_enable)
  CR0[5:4]   = Mode controls (auto_rearm_enable, arm_enable)
  CR0[3:2]   = Reserved
  CR0[1]     = fault_clear (edge-detected)
  CR0[0]     = sw_trigger (edge-detected)

  Option B: Frequency-of-Use Grouping
  CR0[31:29] = FORGE control
  CR0[7]     = hw_trigger_enable
  CR0[6]     = sw_trigger_enable
  CR0[5]     = auto_rearm_enable
  CR0[4]     = Reserved
  CR0[3]     = arm_enable
  CR0[2]     = fault_clear (edge-detected)
  CR0[1]     = Reserved
  CR0[0]     = sw_trigger (edge-detected)

  Option C: Minimal (if we eliminate enable gates)
  CR0[31:29] = FORGE control
  CR0[4]     = hw_trigger_enable (or eliminate?)
  CR0[3]     = auto_rearm_enable
  CR0[2]     = arm_enable
  CR0[1]     = fault_clear (edge-detected)
  CR0[0]     = sw_trigger (edge-detected)

  Question: Which organization makes sense for your typical usage patterns?

##  Q5: . FORGE Bits Location
We are in complete control of the CR0[31:29] FORGE convention. However it was created as a direct result of a desire to easily, consistently, and clearly **gate program execution**. 
when custom bitstreams are loaded on the moku platform they start with **ALL CRS ZEROED** 

These 'FORGE' bits exist so that we can gate control exection at the 'TOP' (@BPD.vhd) and 'shim' (BPD_shim.vhd) layers.

  6. Typical Trigger Workflow

 ## Question: What's the expected usage pattern?
 
Actually, this is an excellent opportunity to describe the 'dual-use' workflows that this bitstream is intended to support (eventually).

## Option one: one off
In this workflow this bitstream will be loaded into a moku slot and will be trigerred once -- either from the network likely, but also potentially the normal InputA comparator

## Option two: 'campaign'
We also want this bitstream to be able to run in 'campaign' mode. In this workflow there is (or likely, will be) another 'higher level state machine'. This is yet to be detailed but would const (roughly speaking) of:
- 'N' number of triggers to process (N=100 - 1024 commonly)
This 'campaign state machine' would be responsible for monitoring the 'one shot' style running and:
	- accumulating a count of faults encountered and tracking across the entire campaign
	- potentially (later) other campaign specific statistics

I hope by considering this now we can cleanly design the interface to the 'one off' method, and perhaps this will influence our overall register scheme. 

---

  Q1: Campaign Mode Register Reservation

  Should we formally reserve CR11-CR15 for campaign mode now? Something like:

  CR11 = campaign_config (enable, trigger_count_target)
  CR12 = campaign_status (current_count, fault_count) [read-back?]
  CR13-CR15 = Reserved for campaign statistics

  Or leave this completely open for future design?

  Q2: Hardware Trigger Gating

  With hw_trigger_enable removed, the InputA comparator will be active whenever global_enable is true. This means:

  - Armed + InputA crosses threshold → FSM fires
  - Not armed + InputA crosses threshold → ignored (FSM not in ARMED state)

  Is this acceptable? The FSM state machine naturally gates triggers (only responds in ARMED state), so explicit enable bits may be redundant.

  Q3: Edge-Detected Bit Ergonomics

  For sw_trigger and fault_clear, the current pattern requires:
  set(FORGE | arm | sw_trigger)  # rising edge
  set(FORGE | arm)               # falling edge (clear)

  Alternative: We could add a hardware "pulse stretcher" that auto-clears internally after N cycles, so software only needs one write. But this adds complexity.

  Preference? Keep explicit clear (current) or add auto-clear?

  Q4: Status Register for Campaign Prep

  Currently state_vector and status_vector are internal signals exported for HVS encoding. For campaign mode, you'll likely want to read FSM state and fault
  counts from Python.

  Should we reserve a status register (read-only from network) now? Moku CloudCompile may have a mechanism for this.
