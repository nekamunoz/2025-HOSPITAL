import argparse
import time
from datetime import datetime
import yaml

from nurses import get_nurse_shift
from historic import get_historic
from rooms import distribute_rooms
from assign import assign_nurses

def load_yaml_config(file_path):
    """
    Load configuration from a YAML file.
    """
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
    """
    Determine the nurse shift based on the current hour.
    """
    if 0 <= hour < 8:  # 00:00 - 07:59 -> Night
        return 'N'
    elif 8 <= hour < 16:  # 08:00 - 15:59 -> Morning
        return 'M'
    else:  # 16:00 - 23:59 -> Afternoon
        return 'T'

def main():
    parser = argparse.ArgumentParser(description="Process nurse shifts and distribute rooms.")
    parser.add_argument('--config', type=str, default=r'config\info.yaml', help='Path to the YAML configuration file.')
    args = parser.parse_args()
    config = load_yaml_config(args.config)
    start_time = time.time()

    # Obtain query_date
    query_date_str = config['excel_info'].get('query_date', datetime.today().strftime('%Y-%m-%d'))
    try:
        query_date = datetime.strptime(query_date_str, '%Y-%m-%d')
    except ValueError:
        print(f"Error: Formato de fecha inválido en query_date: {query_date_str}")
        raise

    # Obtain query_shift
    query_shift = config['excel_info'].get('query_shift')
    if query_shift is None:
        query_shift = config['excel_info'].get('default_shift', get_current_shift(datetime.now().hour))

    # Update config with calculated values for nurses.py
    config['excel_info']['query_date'] = query_date.strftime('%Y-%m-%d')
    config['excel_info']['query_shift'] = query_shift

    # Print the date and shift being processed
    print(f"INFO: Procesando fecha: {query_date.strftime('%Y-%m-%d')}, turno: {query_shift}")

    # Get a list of nurses for a specific shift
    date, shift, nurses = get_nurse_shift(config['excel_info'])

    nurses = list(map(str, nurses))
    print(f"INFO: IDs de las enfermeras {nurses}")
    print(f"INFO: get_nurses_shift took {time.time() - start_time:.2f} seconds")

    # Get the historic data for the given date, shift, nurses and patients
    historic_start = time.time()
    occupied_rooms, rooms_per_control, historic = get_historic(date, shift, nurses, config['paths_historic'])
    print(f"INFO: get_historic took {time.time() - historic_start:.2f} seconds")

    # Create groups of rooms based on the number of nurses per control
    distribute_start = time.time()
    distributed_rooms = distribute_rooms(occupied_rooms, rooms_per_control)
    print(f"INFO: distribute_rooms took {time.time() - distribute_start:.2f} seconds")

    current_date_str = config['excel_info']['query_date']
    current_date = datetime.strptime(current_date_str, '%Y-%m-%d')

    # Assign nurses to the distributed rooms given historic data
    assign_start = time.time()
    best_mapping = assign_nurses(distributed_rooms, nurses, historic, current_date)
    print(f"INFO: assign_nurses took {time.time() - assign_start:.2f} seconds")

    print("Asignación (ID Enfermera, Coste, Num tratamientos): \n", best_mapping)
    print(f"INFO: Total execution time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()