from django.contrib import admin
from .models import Exercise, Workout, WorkoutExercise, WorkoutSession, ExercisePerformance

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
    list_display = ('workout', 'exercise', 'suggested_sets', 'suggested_reps', 'order')
    search_fields = ('workout__name', 'exercise__name')
    list_filter = ('workout', 'exercise')

@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ('workout', 'user', 'started_at', 'finished_at')
    search_fields = ('workout__name', 'user__username')
    list_filter = ('user', 'started_at')

@admin.register(ExercisePerformance)
class ExercisePerformanceAdmin(admin.ModelAdmin):
    list_display = ('workout_session', 'exercise', 'set_number', 'reps', 'weight')
    search_fields = ('workout_session__workout__name', 'exercise__name')
    list_filter = ('workout_session__user', 'exercise')
