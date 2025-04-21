import yaml
import argparse
from nurses import get_nurses_shift
from historic import get_historic
from rooms import distribute_rooms
from assign import assign_nurses
from datetime import datetime, date

def load_yaml(file_path):
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
        if config is None:
            raise ValueError("El archivo YAML está vacío o mal formateado")
        return config
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no se encontró")
        raise
    except yaml.YAMLError as e:
        print(f"Error: Formato inválido en {file_path}: {e}")
        raise

def get_current_shift(hour):
    """Determines the nurses' shift based on the current time."""
    if 0 <= hour < 8:  # 00:00 - 07:59 -> Noche
        return 'N'
    elif 8 <= hour < 16:  # 08:00 - 15:59 -> Mañana
        return 'M'
    else:  # 16:00 - 23:59 -> Tarde
        return 'T'

def main():
    parser = argparse.ArgumentParser(description="Process nurse shifts and distribute rooms.")
    parser.add_argument('--config', type=str, default=r'config\info.yaml', help='Path to the YAML configuration file.')
    args = parser.parse_args()
    config = load_yaml(args.config)

    # Obtain fecha_consulta
    fecha_actual_str = config['excel_info'].get('fecha_consulta', datetime.today().strftime('%Y-%m-%d'))
    try:
        fecha_actual = datetime.strptime(fecha_actual_str, '%Y-%m-%d')
    except ValueError:
        print(f"Error: Formato de fecha inválido en fecha_consulta: {fecha_actual_str}")
        raise

    # Obtain turno_consulta
    turno_consulta = config['excel_info'].get('turno_consulta')
    if turno_consulta is None:
        # Use turno_predeterminado if exists, sotherwise derive from the current time
        turno_consulta = config['excel_info'].get('turno_predeterminado', get_current_shift(datetime.now().hour))

    # Update config with calculated values ​​for nurses.py
    config['excel_info']['fecha_consulta'] = fecha_actual.strftime('%Y-%m-%d')
    config['excel_info']['turno_consulta'] = turno_consulta

    # Print the date and shift being processed
    print(f"Procesando fecha: {fecha_actual.strftime('%Y-%m-%d')}, turno: {turno_consulta}")

    # Get a list of the nurses from a specific shift
    date, shift, nurses = get_nurses_shift(config['excel_info'])

    # Get the historic data for the given date, shift, nurses and patients
    historic, occupied_rooms, nurses_per_control, historial_resume_a_b = get_historic(date, shift, nurses, config['paths_historic'])

    # Create groups of rooms based on the number of nurses per control
    distributed_rooms = distribute_rooms(occupied_rooms, nurses_per_control)

    # Assign nurses to the distributed rooms given historic data
    best_mapping = assign_nurses(distributed_rooms, nurses, historic, historial_resume_a_b, occupied_rooms, fecha_actual)
    print("Asignación (ID Enfermera, Coste, Num tratamientos): ", best_mapping)

if __name__ == "__main__":
    main()