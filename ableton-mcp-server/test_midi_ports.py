import pygame.midi

pygame.midi.init()

print("=== Ports MIDI disponibles ===\n")

count = pygame.midi.get_count()
print(f"Nombre total de ports : {count}\n")

for i in range(count):
    info = pygame.midi.get_device_info(i)
    interface = info[0].decode('utf-8')
    name = info[1].decode('utf-8')
    is_input = info[2]
    is_output = info[3]
    
    port_type = []
    if is_input:
        port_type.append("INPUT")
    if is_output:
        port_type.append("OUTPUT")
    
    print(f"[{i}] {name}")
    print(f"    Interface: {interface}")
    print(f"    Type: {', '.join(port_type)}")
    print()

pygame.midi.quit()