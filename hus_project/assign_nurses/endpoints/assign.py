import os
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from matplotlib.table import Table
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment

from django.conf import settings
save_path = settings.SAVE_PATH

def extract_and_assign_groups(groups):
    extracted_groups = {}
    group_counter = 1
    for control, group_dict in groups.items():
        for key, patient_list in group_dict.items():
            group_name = f"G{group_counter}"
            extracted_groups[group_name] = patient_list
            group_counter += 1
    return extracted_groups

def merge_historial_resume(historic):
    if 'control_A' in historic and 'control_B' in historic:
        merged_historial_treatments = pd.concat([historic['control_A'], historic['control_B']], ignore_index=True)
        return merged_historial_treatments
    else:
        print("Error: Las claves 'control_A' y 'control_B' no están presentes en el diccionario.")
        return None

def count_group_treatments(nurse_id, group, historic):
    count = 0
    for patient_id in group:
        tratamientos = historic[
            (historic['ID_ENF'] == nurse_id) &
            (historic['HABITACION'] == patient_id)
        ]
        count += tratamientos['NUMERO_TRATAMIENTOS'].sum()
    return int(count)

def calculate_cost(group, nurse_id, historic, current_date):
    cost = 0
    for patient_id in group:
        row = historic[
            (historic['ID_ENF'] == nurse_id) &
            (historic['HABITACION'] == patient_id)
        ]     

        if not row.empty:
            date_hist = pd.to_datetime(row.iloc[0]['FECHA_TOMA_MÁS_RECIENTE'])
            difference = relativedelta(current_date, date_hist)
            months = difference.years * 12 + difference.months
            days = difference.days
            months = months + (days / 30)
            if months > 4:
                cost += 2  
            elif months > 2:
                cost += 1  
            else:
                cost += 0  
        else:
            cost += 4
    return cost

def create_branch_schema(nurses, groups, historial_past_treatments, current_date):
    # Create cost matrix for Hungarian algorithm
    n = len(nurses)
    cost_matrix = np.zeros((n, n))
    
    # Fill the cost matrix
    for i, nurse in enumerate(nurses):
        for j, (group_key, group_values) in enumerate(groups.items()):
            cost = calculate_cost(group_values, nurse, historial_past_treatments, current_date)
            treatments = count_group_treatments(nurse, group_values, historial_past_treatments)
            # Store cost in matrix
            cost_matrix[i][j] = cost

    # Apply Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # Create assignment dictionary
    assignment = {}
    total_cost = 0
    total_treatments = 0
    
    for i, j in zip(row_ind, col_ind):
        nurse = nurses[i]
        group_key = list(groups.keys())[j]
        group_values = list(groups.values())[j]
        
        cost = cost_matrix[i][j]
        treatments = count_group_treatments(nurse, group_values, historial_past_treatments)
        
        assignment[group_key] = (nurse, int(cost), treatments)
        total_cost += cost
        total_treatments += treatments

    min_cost_assignments = [(row_ind, assignment, total_cost, total_treatments)]

    if len(min_cost_assignments) == 1:
        best_assignment = min_cost_assignments[0]
    else:
        print("EMPATE DE COSTE")
        best_assignment = max(min_cost_assignments, key=lambda x: x[3])

    best_perm, best_mapping, best_cost, best_treatments = best_assignment
    return best_mapping

def format_mapping(mapping, rooms_lists): 
    for group, rooms in rooms_lists.items():
        if group in mapping:
            lower_limit = rooms[0]
            upper_limit = rooms[-1]
            room_range = f"{lower_limit} - {upper_limit}"
            mapping[group] += (room_range,)
            mapping[group] += (len(rooms),)
            mapping[group] = (mapping[group][0], mapping[group][3], mapping[group][4])
            mapping[f"Grupo {group[1:]}"] = mapping.pop(group)
    return mapping

def create_table(mapping):
    output_path = os.path.join(save_path, 'table.png')
    fig, ax = plt.subplots(figsize=(10, 6)) 
    ax.axis('off')
    table = Table(ax, bbox=[0, 0, 1, 1])
    headers = ['Grupo', 'ID Enfermera', 'Habitaciones', 'Nº Pacientes']

    for col_idx, header in enumerate(headers):
        cell = table.add_cell(0, col_idx, width=1, height=0.5, text=header, loc='center', facecolor='lightgrey')
        cell.get_text().set_fontsize(14)

    for row_idx, (key, values) in enumerate(mapping.items(), start=1):
        cell = table.add_cell(row_idx, 0, width=1, height=0.5, text=key, loc='center', facecolor='white')
        cell.get_text().set_fontsize(12)
        for col_idx, value in enumerate(values, start=1):
            cell = table.add_cell(row_idx, col_idx, width=1, height=0.5, text=value, loc='center', facecolor='white')
            cell.get_text().set_fontsize(12)

    ax.add_table(table)
    ax.set_axis_off()
    plt.title(f'Tabla de asignación de enfermeras')
    plt.savefig(output_path, bbox_inches='tight')

def assign_nurses(distributed_rooms, nurses_list, historic, current_date):
    # Get a dict of all rooms dictionaries
    all_groups = extract_and_assign_groups(distributed_rooms)

    # Merge historic data form 
    historial_past_treatments = merge_historial_resume(historic)
    best_mapping = create_branch_schema(nurses_list, all_groups, historial_past_treatments, current_date)

    create_table(format_mapping(best_mapping, all_groups))

    return best_mapping
    