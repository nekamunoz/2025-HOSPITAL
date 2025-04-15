import yaml
import argparse

from nurses import get_nurses_shift
from historic import get_historic
from rooms import distribute_rooms
from assign import assign_nurses

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def main():
    parser = argparse.ArgumentParser(description="Process nurse shifts and distribute rooms.")
    parser.add_argument('--config', type=str, default=r'config\info.yaml', help='Path to the YAML configuration file.')
    args = parser.parse_args()
    config = load_yaml(args.config)

    # Get a list of the nurses from a specific shift
    date, shift, nurses = get_nurses_shift(config['excel_info'])

    # Get the historic data for the given date, shift, nurses and patients
    historic, occupied_rooms, nurses_per_control = get_historic(date, shift, nurses, config['paths_historic'])

    # Create groups of rooms based on the number of nurses per control
    distributed_rooms = distribute_rooms(occupied_rooms, nurses_per_control)

    # Assign nurses to the distributed rooms given historic data
    best_mapping = assign_nurses(distributed_rooms, nurses, historic, occupied_rooms)
    print("Assignment:", best_mapping)

if __name__ == "__main__":
    main()
