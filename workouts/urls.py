from django.urls import path
from . import views

app_name = 'workouts'

urlpatterns = [
    path('', views.index, name='index'),
    path('exercises/', views.ExerciseListView.as_view(), name='exercise_list'),
]
