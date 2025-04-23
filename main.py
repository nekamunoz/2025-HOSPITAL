import yaml
import argparse

from nurses import get_nurses_shift
from historic import get_historic
from rooms import distribute_rooms
from assign import assign_nurses
from datetime import datetime
import time

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def main():
    parser = argparse.ArgumentParser(description="Process nurse shifts and distribute rooms.")
    parser.add_argument('--config', type=str, default=r'config\info.yaml', help='Path to the YAML configuration file.')
    args = parser.parse_args()
    config = load_yaml(args.config)

    # Start timing
    start_time = time.time()

    # Get a list of the nurses from a specific shift
    date, shift, nurses = get_nurses_shift(config['excel_info'])
    nurses = list(map(str, nurses))
    print(f"INFO: get_nurses_shift took {time.time() - start_time:.2f} seconds")

    # Get the historic data for the given date, shift, nurses and patients
    historic_start = time.time()
    occupied_rooms, rooms_per_control, historic = get_historic(date, shift, nurses, config['paths_historic'])
    print(f"INFO: get_historic took {time.time() - historic_start:.2f} seconds")

    # Create groups of rooms based on the number of nurses per control
    distribute_start = time.time()
    distributed_rooms = distribute_rooms(occupied_rooms, rooms_per_control)
    print(f"INFO: distribute_rooms took {time.time() - distribute_start:.2f} seconds")

    current_date_str = config['excel_info']['fecha_consulta']
    current_date = datetime.strptime(current_date_str, '%Y-%m-%d')

    # Assign nurses to the distributed rooms given historic data
    assign_start = time.time()
    best_mapping = assign_nurses(distributed_rooms, nurses, historic, current_date)
    print(f"INFO: assign_nurses took {time.time() - assign_start:.2f} seconds")

    print("Asignación (ID Enfermera, Coste, Num tratamientos): \n", best_mapping)
    print(f"INFO: Total execution time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
