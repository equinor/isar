# To generate state transition diagram

The 'update_state_diagram.py' file can be used to generate a state transition
diagram of the ISAR state machine. To do so, simply run the file from the top
level folder (it assumes that the main folder is the current woking directory).
This will then generate a .mmd file (diagram.mmd), which is a Mermaid markdown
file, which can be converted to other formats if needed.

To convert a .mmd file to a .svg file, first run 

    npm install -g @mermaid-js/mermaid-cli

and then

    mmdc -i diagram.mmd -o diagram.svg

This can then be opened with a browser. Other formats such as PNG are supported,
but the resolution can be a limitation for large diagrams.

# Limitations

Currently the script assumes that all transitions from one state to another
are made within each state file. This would not be the case if a utility
function or some other imported function made the transition call instead. This
is because it generates the transitions based on which states are imported from
another state. If no import statement is found, then we assume that there is
not a transition.
