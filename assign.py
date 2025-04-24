from itertools import permutations
from dateutil.relativedelta import relativedelta
import pandas as pd
from scipy.optimize import linear_sum_assignment
import numpy as np

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


def assign_nurses(distributed_rooms, nurses_list, historic, current_date):
    # Get a dict of all rooms dictionaries
    all_groups = extract_and_assign_groups(distributed_rooms)

    # Merge historic data form 
    historial_past_treatments = merge_historial_resume(historic)
    best_mapping = create_branch_schema(nurses_list, all_groups, historial_past_treatments, current_date)
    return best_mapping
    