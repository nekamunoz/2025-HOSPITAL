import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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

def extract_historial(file_path):
    try:
        historial_df = pd.read_excel(file_path)
        historial_df['ID_ENF'] = historial_df['ID_ENF'].fillna(0).astype(int)
        historial_df['FECHA_TOMA'] = pd.to_datetime(historial_df['FECHA_TOMA']).dt.date
        return historial_df
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None

def filter_last_6_months(historial_df, fecha_actual):
    fecha_limite = fecha_actual - timedelta(days=6*30)
    historial_df['FECHA_TOMA'] = pd.to_datetime(historial_df['FECHA_TOMA']).dt.date
    filtered_df = historial_df[
        (historial_df['FECHA_TOMA'] >= fecha_limite) &
        (historial_df['FECHA_TOMA'] <= fecha_actual)
    ]
    return filtered_df

def calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict):
    patients_in_a = len(control_a_dict)
    patients_in_b = len(control_b_dict)
    total_patients = patients_in_a + patients_in_b
    nurses_in_a = round((patients_in_a / total_patients) * total_nurses)
    nurses_in_b = total_nurses - nurses_in_a
    return nurses_in_a, nurses_in_b

def number_rooms_per_nurses_per_control(control_a_dict, control_b_dict, nurses_in_a, nurses_in_b, turno):
    if turno in ["M", "T"]:
        max_patients_per_nurse = 11
    elif turno == "N":
        max_patients_per_nurse = 17
    else:
        raise ValueError("Turno no válido. Debe ser 'M', 'T' o 'N'.")
    
    def dividir(control_dict, nurses):
        total = len(control_dict)
        base = total // nurses
        remainder = total % nurses
        return [base + (1 if i < remainder else 0) for i in range(nurses)]

    rooms_count_a = dividir(control_a_dict, nurses_in_a)
    rooms_count_b = dividir(control_b_dict, nurses_in_b)

    if any(count > max_patients_per_nurse for count in rooms_count_a + rooms_count_b):
        print("⚠️  Falta personal: Hay enfermeras con más pacientes del límite permitido.")

    return rooms_count_a, rooms_count_b

def treatment_historial(control_a_dict, control_b_dict, filtered_historial, enfermeras_turno):
    def proccess_historial(control_dict):
        historial = filtered_historial[
            (filtered_historial['ID_PACIENTE'].isin(control_dict)) &
            (filtered_historial['ID_ENF'].isin(enfermeras_turno))].copy()
        resumen = historial.groupby(['ID_ENF', 'ID_PACIENTE']).agg(
            NUMERO_TRATAMIENTOS=('ID_ENF', 'count'),
            FECHA_TOMA_MÁS_RECIENTE=('FECHA_TOMA', 'max')).reset_index()

        resumen['HABITACION'] = resumen['ID_PACIENTE'].map(control_dict)

        resumen['HABITACION_ORDEN'] = resumen['HABITACION'].apply(
            lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
        resumen = resumen.sort_values(by='HABITACION_ORDEN').drop(columns=['HABITACION_ORDEN'])
        return resumen

    historial_a = proccess_historial(control_a_dict)
    historial_b = proccess_historial(control_b_dict)
    return {'A': historial_a, 'B': historial_b }


def generate_treatment_lists_by_nurse_from_summary(historial_resume_a_b, control_a_dict, control_b_dict, enfermeras_turno):
    habitaciones_a = sorted(control_a_dict.values(), key=lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
    habitaciones_b = sorted(control_b_dict.values(), key=lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
    treatment_lists = {}

    for enfermera in enfermeras_turno:
        def construir_lista(habs, resumen_df, control_dict):
            lista = []
            for hab in habs:
                paciente_id = next((k for k, v in control_dict.items() if v == hab), None)
                if paciente_id is not None:
                    tratamientos = resumen_df[
                        (resumen_df['ID_ENF'] == enfermera) & (resumen_df['ID_PACIENTE'] == paciente_id)
                    ]['NUMERO_TRATAMIENTOS']
                    lista.append(int(tratamientos.iloc[0]) if not tratamientos.empty else 0)
                else:
                    lista.append(0)
            return lista

        resumen_a = historial_resume_a_b['A']
        resumen_b = historial_resume_a_b['B']
        treatment_lists[enfermera] = {
            'Control A': construir_lista(habitaciones_a, resumen_a, control_a_dict),
            'Control B': construir_lista(habitaciones_b, resumen_b, control_b_dict)
        }

    return treatment_lists

def main(fecha_actual, turno, enfermeras_turno):
    # Rutas de archivos
    file_ingresados = r'data\Ingresados.xlsx' # EXTRAER
    file_historial = r'data\hcoIngresos.xlsx' # EXTRAER

    # Extracción de datos
    control_a_dict, control_b_dict = extract_patient_bed(file_ingresados)
    historial = extract_historial(file_historial)
    filtered_historial = filter_last_6_months(historial, fecha_actual)

    # Asignación de enfermeras
    total_nurses = len(enfermeras_turno)
    nurses_in_a, nurses_in_b = calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict)
    rooms_count_a, rooms_count_b = number_rooms_per_nurses_per_control(control_a_dict, control_b_dict, nurses_in_a, nurses_in_b, turno)

    # Generar resúmenes de tratamientos por enfermera para ambos controles A y B
    historial_resume_a_b = treatment_historial(control_a_dict, control_b_dict, filtered_historial, enfermeras_turno)

    # Generar las listas de tratamientos por enfermera a partir del resumen
    treatment_lists = generate_treatment_lists_by_nurse_from_summary(
        historial_resume_a_b, control_a_dict, control_b_dict, enfermeras_turno
    )

    # Mostrar resultados
    print(f"\n--- Distribución Habitaciones ---\nControl A: {rooms_count_a}\nControl B: {rooms_count_b}")
    for enfermera, controles in treatment_lists.items():
        print(f"\nEnfermera {enfermera}:")
        print(f"  Control A: {controles['Control A']}")
        print(f"  Control B: {controles['Control B']}")

    return treatment_lists, control_a_dict, control_b_dict

if __name__ == "__main__":
    main()