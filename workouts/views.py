from django.shortcuts import render
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import Exercise, Workout, WorkoutExercise

class ExerciseListView(LoginRequiredMixin, ListView):
    model = Exercise
    template_name = 'workouts/exercise_list.html'
    context_object_name = 'exercises'
    login_url = 'accounts:login'

@login_required(login_url='accounts:login')
def index(request):
    return render(request, 'workouts/index.html', {
        'total_exercises': Exercise.objects.count(),
        'total_workouts': Workout.objects.filter(user=request.user).count(),  # Only count user's workouts
    })
