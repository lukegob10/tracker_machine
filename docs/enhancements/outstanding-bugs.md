# List of Currently Known Bugs

- Solutions view: when toggling phases for a selected solution, the selected project/solution becomes unselected (drops context).  
  - Repro: select a solution, open its phases, enable/disable a phase.  
  - Expected: keep the same project/solution selected.  
  - Actual: selection clears, forcing re-selection and breaking edit flow.
