
Claude,
There are a few interrelated concerns I want your help addressing. 

## T0: when do (or more accurately, __should__ we make network updated control registers visible (L1-TOP) to L2 (shim) and L3 (main).

As currently implemented the bitstream is riddled with (potential, if not practical) race conditions because the network register updates are completely asyncronous with the bitstream operation.

I think we should take some more responsibility for managing this, and I hope that we can limit the changes to the L1-top / L2-shim layer system.


This touches on some related issues:
- T1: 'reset' behavior: Should we simply change the DPD_main.vhd file so that it copies (latches?) the incoming app_reg values during reset? 
- T2: 'clearing faults': This also seems like it could be made equivalent with reset


Things to consider: 
- We could create an outbound signal from the 'BPD_main.vhd' entity 'ready_for_updates' - this would signal to the shim that the 'main' application is in a safe state for changing its network registers
another option
- modify the state machine so that it goes from RESET->INITIALIZING (accepting updates -- provides a known / well-defined place for 'main' to perform some form in app specific input parameter validation and then transition to FAULT state on invalid inputs). 

In our case, we are not particularly timing sensitive during 'startup'. This makes the 
RESET->Initializing->IDLE approach appealing.


