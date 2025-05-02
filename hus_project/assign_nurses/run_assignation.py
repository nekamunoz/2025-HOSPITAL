import time
from .endpoints.nurses import get_nurse_shift
from .endpoints.historic import get_historic
from .endpoints.rooms import distribute_rooms
from .endpoints.assign import assign_nurses

def main(query_date, query_shift):
    start_time = time.time()
    str_date = query_date.strftime("%Y-%m-%d")

    # Print the date and shift being processed
    print(f"[INFO]: Procesando fecha: {str_date}, turno: {query_shift}")

    # Get a list of nurses for a specific shift
    date, shift, nurses = get_nurse_shift(query_date, query_shift)
    
    print(f"[INFO]: IDs de las enfermeras {nurses}")
    print(f"[INFO]: get_nurses_shift took {time.time() - start_time:.2f} seconds")

    # Get the historic data for the given date, shift, nurses and patients
    historic_start = time.time()
    occupied_rooms, rooms_per_control, historic = get_historic(date, shift, nurses)
    print(f"[INFO]: get_historic took {time.time() - historic_start:.2f} seconds")

    # Create groups of rooms based on the number of nurses per control
    distribute_start = time.time()
    distributed_rooms = distribute_rooms(occupied_rooms, rooms_per_control, str_date, query_shift)
    print(f"[INFO]: distribute_rooms took {time.time() - distribute_start:.2f} seconds")

    # Assign nurses to the distributed rooms given historic data
    assign_start = time.time()
    best_mapping = assign_nurses(distributed_rooms, nurses, historic, query_date, str_date, query_shift)
    print(f"[INFO]: assign_nurses took {time.time() - assign_start:.2f} seconds")

    print(f"[INFO]: Asignación: \n {best_mapping}")
    print(f"[INFO]: Total execution time: {time.time() - start_time:.2f} seconds")

    return best_mapping

if __name__ == "__main__":
    main()