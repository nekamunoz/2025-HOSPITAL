import json
import os
from itertools import permutations

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from django.conf import settings
save_path = settings.SAVE_PATH
file_controls = settings.FILE_CONTROLS

def load_controls(control_list, control_path):
    controls_path = os.path.join(control_path)

    control_dict = {}
    with open(controls_path, 'r') as file:
        data = json.load(file)
        for control in control_list:
            if control in data:
                control_dict[control] = {room["room"]: (room["x"], room["y"]) for room in data[control]}
    return control_dict

def create_room_groups(rooms, rooms_per_group):
    rooms.sort(key=lambda room: room[0])

    unique_perms = set(list(permutations(rooms_per_group)))
    lowest_i = float('inf')
    best_grouped_rooms = []

    for perm in unique_perms:
        rooms_per_group = list(perm)
        grouped_rooms = []
        start_index = 0

        for group_size in rooms_per_group:
            end_index = start_index + group_size
            grouped_rooms.append(rooms[start_index:end_index])
            start_index = end_index

        i = 0
        for group in grouped_rooms:
            for room in group:
                room_id = room[0]
                if room_id.endswith('B') and (room_id[:-1]) not in [r[0] for r in group]:
                    i += 1
        if i < lowest_i:
            lowest_i = i
            best_grouped_rooms = grouped_rooms

    final_groups = {}
    for i, group in enumerate(best_grouped_rooms):
        group = [room[0] for room in group]
        final_groups[i] = group
    return best_grouped_rooms, final_groups

def plot_room_distribution(floor_coord, groups_coords, n_groups, query_date, query_shift, w=1, h=1):
    output_path = os.path.join(save_path, 'rooms.png')
    cmap = plt.get_cmap('tab20', n_groups)
    group_colors = cmap.colors

    plt.figure(figsize=(14, 8))
    ax = plt.gca()
    ax = plt.gca()
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    global_group_idx = 0

    for control, groups in groups_coords.items():
        for room, (x, y) in floor_coord[control].items():
            rect = Rectangle((x, y), w, h, edgecolor='black', facecolor='lightgray', alpha=0.5)
            ax.add_patch(rect)

        for group in groups:
            room_coords = [(x, y) for _, (x, y) in group]

            for room, (x, y) in group:
                color = group_colors[global_group_idx % len(group_colors)]
                rect = Rectangle((x, y), w, h, edgecolor='black', facecolor=color)
                ax.add_patch(rect)
                ax.text(x + w/2, y + h/2, room, color='black', ha='center', va='center', fontsize=8)

            center_x = np.mean([x + w/2 for x, y in room_coords])
            center_y = np.mean([y + h/2 for x, y in room_coords])
            ax.text(center_x, center_y, f"Grupo {global_group_idx + 1}\n{len(group)} camas", color='white', ha='center', va='center', fontsize=10, bbox=dict(facecolor='black', alpha=0.5))

            global_group_idx += 1

    plt.title(f'Distribución para el turno {query_shift} del {query_date}')
    plt.grid(True, color='black', linestyle='--', alpha=0.3)  
    plt.axis('equal')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')


def distribute_rooms(floor_occ_rooms, floor_patients, query_date, query_shift):
    control_names = list(floor_occ_rooms.keys())
    floor_coord = load_controls(control_names, file_controls)
    
    floor_occu_rooms_coord = {}
    for control, rooms in floor_occ_rooms.items():
        rooms_list = rooms if isinstance(rooms, (list, set)) else [rooms]
        floor_occu_rooms_coord[control] = {
            room: floor_coord[control][room] 
            for room in rooms_list 
            if room in floor_coord[control]
        }

    groups_lists = {}
    groups_coord = {}
    for control in control_names:
        rooms_items = list(floor_occu_rooms_coord[control].items())
        grouped_rooms, grouped_list = create_room_groups(rooms_items, floor_patients[control])
        groups_lists[control] = grouped_list
        groups_coord[control] = grouped_rooms
    
    n_groups = sum(len(v) for v in floor_patients.values())
    plot_room_distribution(floor_coord, groups_coord, n_groups, query_date, query_shift)

    return groups_lists
