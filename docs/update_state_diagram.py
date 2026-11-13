from isar.models.events import Events
from isar.state_machine.state_machine import collect_edges, to_mermaid

if __name__ == "__main__":
    with open("diagram.mmd", "w") as file:
        file.write(to_mermaid(collect_edges(Events())))
