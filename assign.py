from itertools import permutations

def extract_and_assign_groups(groups):
    extracted_groups = {}
    group_counter = 1
    for control, group_dict in groups.items():
        for key, patient_list in group_dict.items():
            group_name = f"G{group_counter}"
            extracted_groups[group_name] = patient_list
            group_counter += 1
    return extracted_groups

def merge_controls(history):
    merged_history = {}
    for nurse, controls in history.items():
        merged_history[nurse] = controls['control_A'] + controls['control_B']
    return merged_history

def get_patient_index(patients, patient_number):
    try:
        return patients.index(patient_number)
    except ValueError:
        return -1

def calculate_cost(group, nurse_history, patients):
    cost = 0
    for patient_id in group:
        patient_index = get_patient_index(patients, patient_id)
        if nurse_history[patient_index] == 0:
            cost += 1
    return cost

def create_branch_schema(nurses, groups, history, patients):
    all_assignments = []

    for perm in permutations(nurses):
        total_cost = 0
        assignment = {}
        
        for i, nurse in enumerate(perm):
            group_key = list(groups.keys())[i]
            group_values = list(groups.values())[i]
            cost = calculate_cost(group_values, history[nurse], patients)
            total_cost += cost
            
            assignment[group_key] = (nurse, cost)
        
        all_assignments.append((perm, assignment, total_cost))
    
    return all_assignments


def assign_nurses(distributed_rooms, nurses_list, historic, patients):
    all_groups = extract_and_assign_groups(distributed_rooms)
    merged_historic = merge_controls(historic)
    patients = patients['control_A'] + patients['control_B']

    all_assignments = create_branch_schema(nurses_list, all_groups, merged_historic, patients)
    best_assignment = min(all_assignments, key=lambda x: x[2])
    best_perm, best_mapping, best_cost = best_assignment

    return best_mapping
    