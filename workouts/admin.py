from django.contrib import admin
from .models import Exercise, Workout, WorkoutExercise

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'target_muscle', 'created_at')
    search_fields = ('name', 'description', 'target_muscle')
    list_filter = ('target_muscle',)

@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('user', 'created_at')

@admin.register(WorkoutExercise)
class WorkoutExerciseAdmin(admin.ModelAdmin):
    list_display = ('workout', 'exercise', 'sets', 'reps', 'weight', 'order')
    search_fields = ('workout__name', 'exercise__name')
    list_filter = ('workout', 'exercise')
