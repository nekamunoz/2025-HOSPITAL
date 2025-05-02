from datetime import datetime

def get_current_shift(hour):
    """ Determine the current shift based on the hour of the day. """

    if 8 <= hour < 15:
        return 'M'
    elif 15 <= hour < 22:
        return 'T'
    else:
        return 'N'
    
def get_current_query_params():
    """ Get the current date and shift. """
    query_date = datetime.today()
    query_shift = get_current_shift(datetime.now().hour)
    return query_date, query_shift

def parse_date(date_str):
    """ Parse a date string into a datetime object. """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

def parse_shift(shift_str):
    """ Parse a shift string into its shorthand or full name. """
    shift_map = {'Mañana': 'M', 'Tarde': 'T', 'Noche': 'N'}
    inverse_map = {v: k for k, v in shift_map.items()}
    if shift_str in shift_map:
        return shift_map[shift_str]
    elif shift_str in inverse_map:
        return inverse_map[shift_str]
    else:
        raise ValueError("Invalid shift. Expected 'M', 'T', 'N' or 'Mañana', 'Tarde', 'Noche'.")