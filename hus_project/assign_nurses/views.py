from django.shortcuts import redirect
from django.shortcuts import render
from django.http import JsonResponse
from . import run_assignation
from .endpoints import utils

def index(request):
    current_date, current_shift = utils.get_current_query_params()
    context = {
        'current_date': current_date.strftime("%Y-%m-%d"),
        'current_shift': current_shift
    }
    return render(request, 'index.html', context)

def assignation(request):
    if request.method == "POST":
        selected_date = request.POST.get("date")
        selected_shift = request.POST.get("shift")
        context = {
            "selected_date": selected_date,
            "selected_shift": selected_shift
        }
        return render(request, "assignation.html", context)
    return redirect('index')

def run_main(request):
    selected_date = request.GET.get('date')
    selected_shift = request.GET.get('shift')
    if selected_date and selected_shift:
        query_date = utils.parse_date(selected_date)
        query_shift = utils.parse_shift(selected_shift)
    else:
        return JsonResponse({'error': 'Invalid date or shift'}, status=400)
    result = run_assignation.main(query_date, query_shift)
    return JsonResponse({'data': result})