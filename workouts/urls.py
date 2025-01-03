from django.urls import path
from . import views

app_name = 'workouts'

urlpatterns = [
    path('', views.index, name='index'),
    path('exercises/', views.ExerciseListView.as_view(), name='exercise_list'),
    path('exercises/add/', views.ExerciseCreateView.as_view(), name='exercise_create'),
    path('exercises/<int:pk>/edit/', views.ExerciseUpdateView.as_view(), name='exercise_edit'),
    path('exercises/<int:pk>/delete/', views.ExerciseDeleteView.as_view(), name='exercise_delete'),
    path('workouts/', views.WorkoutListView.as_view(), name='workout_list'),
    path('workouts/add/', views.WorkoutCreateView.as_view(), name='workout_create'),
    path('workouts/<int:pk>/', views.WorkoutDetailView.as_view(), name='workout_detail'),
    path('workouts/<int:pk>/edit/', views.WorkoutUpdateView.as_view(), name='workout_edit'),
    path('workouts/<int:pk>/delete/', views.WorkoutDeleteView.as_view(), name='workout_delete'),
    path('workouts/add-exercise-form/', views.add_exercise_form, name='add_exercise_form'),
    path('sessions/', views.WorkoutSessionListView.as_view(), name='session_list'),
    path('sessions/start/', views.start_workout_session, name='start_session'),
    path('sessions/<int:pk>/', views.WorkoutSessionDetailView.as_view(), name='session_detail'),
    path('sessions/<int:session_pk>/performance/<int:performance_pk>/delete/',
         views.DeletePerformanceView.as_view(), name='delete_performance'),
]
