import pandas as pd
from datetime import timedelta

def extract_patient_bed(file_path):
    df = pd.read_excel(file_path)
    df_4thfloor = df[df['CAMA'].astype(str).str.startswith('4')]
    beds_and_patients = df_4thfloor[['CAMA', 'ID_PACIENTE']].values.tolist()
    beds_and_patients.sort(key=lambda x: (int(''.join(filter(str.isdigit, str(x[0])))), str(x[0])))
    patient_bed_mapping = {patient[1]: patient[0] for patient in beds_and_patients}
    control_a, control_b = {}, {}
    for patient_id, bed in patient_bed_mapping.items():
        bed_number = int(''.join(filter(str.isdigit, bed)))
        if bed_number < 431:
            control_a[patient_id] = bed
        else:
            control_b[patient_id] = bed
    return control_a, control_b

def calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict):
    patients_in_a = len(control_a_dict)
    patients_in_b = len(control_b_dict)
    total_patients = patients_in_a + patients_in_b
    nurses_in_a = round((patients_in_a / total_patients) * total_nurses)
    nurses_in_b = total_nurses - nurses_in_a
    return {"control_A": nurses_in_a, "control_B": nurses_in_b}

def number_rooms_per_nurses_per_control(control_a_dict, control_b_dict, nurses_per_control, shift):
    if shift in ["M", "T"]:
        max_patients_per_nurse = 11
    elif shift == "N":
        max_patients_per_nurse = 17
    else:
        raise ValueError("Turno no válido. Debe ser 'M', 'T' o 'N'.")
    
    def divide(control_dict, nurses):
        total = len(control_dict)
        base = total // nurses
        remainder = total % nurses
        return [base + (1 if i < remainder else 0) for i in range(nurses)]

    rooms_count_a = divide(control_a_dict, nurses_per_control['control_A'])
    rooms_count_b = divide(control_b_dict, nurses_per_control['control_B'])

    if any(count > max_patients_per_nurse for count in rooms_count_a + rooms_count_b):
        print("⚠️  Falta personal: Hay enfermeras con más pacientes del límite permitido.")

    return {"control_A": rooms_count_a, "control_B": rooms_count_b}

def treatment_historial(filepath, control_a_dict, control_b_dict, nurses_shift, current_date):
    historic_df = pd.read_excel(filepath)
    historic_df['FECHA_TOMA'] = pd.to_datetime(historic_df['FECHA_TOMA'], errors='coerce')

    def proccess_historial(control_dict, historic_df, current_date):
        try:
            
            historic_df['ID_ENF'] = historic_df['ID_ENF'].fillna(0).astype(int).astype(str)
            historic_df['ID_PACIENTE'] = historic_df['ID_PACIENTE'].astype(int)  
            # nurses_shift_str = list(map(str, nurses_shift)) 
            mask = historic_df['ID_PACIENTE'].isin(control_dict) & historic_df['ID_ENF'].isin(nurses_shift)
            historic = historic_df.loc[mask].copy()
            historic = historic[historic['ID_ENF'].isin(nurses_shift)]

            historic['ID_ENF'] = (
                historic['ID_ENF']
                .fillna(0)
                .astype(int)
                .astype(str)
            )

            historic['FECHA_TOMA'] = pd.to_datetime(historic['FECHA_TOMA'], errors= 'coerce').dt.date
            limit_date = current_date - timedelta(days=6*30)  # Last 6 months filter
            historic = historic[
                (historic['FECHA_TOMA'] >= limit_date) & 
                (historic['FECHA_TOMA'] <= current_date)  
            ]
            
            agg_funcs = {'ID_ENF': 'count', 'FECHA_TOMA': 'max'}
            resume = historic.groupby(['ID_ENF', 'ID_PACIENTE']).agg(agg_funcs).rename(
                columns={'ID_ENF': 'NUMERO_TRATAMIENTOS', 'FECHA_TOMA': 'FECHA_TOMA_MÁS_RECIENTE'}
            ).reset_index()
            
            resume['HABITACION'] = resume['ID_PACIENTE'].map(control_dict)
            
            resume['HABITACION_ORDEN'] = resume['HABITACION'].apply(
                lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
            resume = resume.sort_values(by='HABITACION_ORDEN').drop(columns=['HABITACION_ORDEN'])
            return resume
        
        except Exception as e:
            print(f"Error al leer el archivo: {e}")
            return None
        
    historic_a = proccess_historial(control_a_dict, historic_df, current_date)
    historic_b = proccess_historial(control_b_dict, historic_df, current_date)
    return {'control_A': historic_a, 'control_B': historic_b }

def get_historic(current_date, shift, shift_nurses, config):
    # Mapping of patients IDs to beds numbers for controls A and B
    control_a_dict, control_b_dict = extract_patient_bed(config['file_hosp'])

    # Get rooms division based on the number of nurses
    total_nurses = len(shift_nurses)
    nurses_per_control = calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict)
    rooms_per_control = number_rooms_per_nurses_per_control(control_a_dict, control_b_dict, nurses_per_control, shift)

    # Generate summaries of treatments by nurse for both controls A and B
    historial_resume_a_b = treatment_historial(config['file_historic'], control_a_dict, control_b_dict, shift_nurses, current_date)

    # Generate a list of occupied rooms for each control
    occupied_rooms_per_control = {"control_A": list(control_a_dict.values()),"control_B": list(control_b_dict.values())}

    return occupied_rooms_per_control, rooms_per_control, historial_resume_a_b





