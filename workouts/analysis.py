from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Count, F, ExpressionWrapper, FloatField
from django.db.models.functions import ExtractWeek, ExtractYear
from .models import ExercisePerformance, WorkoutSession, WorkoutExercise
import pandas as pd
import plotly.express as px

@login_required
def workout_analysis(request):
    # Get user's workout data
    performances = ExercisePerformance.objects.filter(
        workout_session__user=request.user,
        workout_session__finished_at__isnull=False
    ).select_related('exercise', 'workout_session')
    
    if not performances.exists():
        messages.info(request, "No completed workout sessions found. Complete some workouts to see your progress!")
        return render(request, 'workouts/analysis.html')
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(list(performances.values(
        'exercise__name', 'reps', 'weight', 'performed_at',
        'workout_session__started_at', 'workout_session__finished_at'
    )))
    
    # 1. Weight Progression
    weight_progress = {}
    for exercise in df['exercise__name'].unique():
        exercise_data = df[df['exercise__name'] == exercise]
        fig = px.line(
            exercise_data,
            x='performed_at',
            y='weight',
            title=f'Weight Progression - {exercise}',
            labels={'weight': 'Weight (kg)', 'performed_at': 'Date'}
        )
        weight_progress[exercise] = fig.to_html(full_html=False)
    
    # 2. Volume Progression (weight × reps)
    df['volume'] = df['weight'] * df['reps']
    volume_progress = {}
    for exercise in df['exercise__name'].unique():
        exercise_data = df[df['exercise__name'] == exercise]
        daily_volume = exercise_data.groupby('performed_at')['volume'].sum().reset_index()
        fig = px.line(
            daily_volume,
            x='performed_at',
            y='volume',
            title=f'Volume Progression - {exercise}',
            labels={'volume': 'Volume (kg × reps)', 'performed_at': 'Date'}
        )
        volume_progress[exercise] = fig.to_html(full_html=False)
    
    # 3. Workout Frequency Analysis
    sessions = WorkoutSession.objects.filter(
        user=request.user,
        finished_at__isnull=False
    ).annotate(
        week=ExtractWeek('started_at'),
        year=ExtractYear('started_at')
    ).values('week', 'year').annotate(
        count=Count('id')
    ).order_by('year', 'week')
    
    freq_data = pd.DataFrame(list(sessions))
    if not freq_data.empty:
        fig = px.bar(
            freq_data,
            x='week',
            y='count',
            title='Workouts per Week',
            labels={'count': 'Number of Workouts', 'week': 'Week Number'}
        )
        workout_frequency = fig.to_html(full_html=False)
    else:
        workout_frequency = None
    
    # 4. Personal Records
    prs = {}
    for exercise in df['exercise__name'].unique():
        exercise_data = df[df['exercise__name'] == exercise]
        prs[exercise] = {
            'max_weight': exercise_data['weight'].max(),
            'max_volume': exercise_data['volume'].max(),
            'max_reps': exercise_data['reps'].max(),
            'total_volume': exercise_data['volume'].sum()
        }
    
    # 5. Exercise Completion Rate
    completion_data = WorkoutExercise.objects.filter(
        workout__user=request.user
    ).annotate(
        completed_count=Count('workout__workoutsession__exerciseperformance',
                            filter=models.Q(
                                workout__workoutsession__exerciseperformance__exercise=F('exercise')
                            ))
    ).values('exercise__name').annotate(
        completion_rate=ExpressionWrapper(
            F('completed_count') * 100.0 / Count('workout__workoutsession'),
            output_field=FloatField()
        )
    )
    
    completion_df = pd.DataFrame(list(completion_data))
    if not completion_df.empty:
        fig = px.bar(
            completion_df,
            x='exercise__name',
            y='completion_rate',
            title='Exercise Completion Rate',
            labels={'completion_rate': 'Completion Rate (%)', 'exercise__name': 'Exercise'}
        )
        completion_chart = fig.to_html(full_html=False)
    else:
        completion_chart = None
    
    # 6. Rest Time Analysis
    rest_times = []
    for exercise in df['exercise__name'].unique():
        exercise_data = df[df['exercise__name'] == exercise].sort_values('performed_at')
        if len(exercise_data) > 1:
            rest_time = exercise_data['performed_at'].diff().mean()
            if pd.notnull(rest_time):
                rest_times.append({
                    'exercise': exercise,
                    'avg_rest': rest_time.total_seconds() / 60  # Convert to minutes
                })
    
    rest_df = pd.DataFrame(rest_times)
    if not rest_df.empty:
        fig = px.bar(
            rest_df,
            x='exercise',
            y='avg_rest',
            title='Average Rest Time Between Sets',
            labels={'avg_rest': 'Rest Time (minutes)', 'exercise': 'Exercise'}
        )
        rest_chart = fig.to_html(full_html=False)
    else:
        rest_chart = None
    
    context = {
        'weight_progress': weight_progress,
        'volume_progress': volume_progress,
        'workout_frequency': workout_frequency,
        'personal_records': prs,
        'completion_chart': completion_chart,
        'rest_chart': rest_chart,
    }
    
    return render(request, 'workouts/analysis.html', context) 