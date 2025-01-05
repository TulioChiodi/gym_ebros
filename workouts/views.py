from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction, models
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db.models import Max, Avg, Count, F, ExpressionWrapper, FloatField, Q
from django.db.models.functions import ExtractWeek, ExtractYear
from .models import Exercise, Workout, WorkoutExercise, WorkoutSession, ExercisePerformance
from .forms import (
    ExerciseForm, WorkoutForm, WorkoutExerciseFormSet,
    WorkoutSessionForm, ExercisePerformanceForm, ExercisePerformanceFormSet
)
from django.core.exceptions import ValidationError
import logging
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

# Set up logger
logger = logging.getLogger(__name__)

def debug_form_data(request, form=None, formset=None):
    """Helper function to log form data and errors"""
    logger.debug("==== Form Debug Information ====")
    
    # Log request method and path
    logger.debug(f"Request Method: {request.method}")
    logger.debug(f"Request Path: {request.path}")
    
    # Log POST data
    logger.debug("POST Data:")
    for key, value in request.POST.items():
        logger.debug(f"  {key}: {value}")
    
    # Log main form errors if exists
    if form and hasattr(form, 'errors'):
        logger.debug("Main Form Errors:")
        logger.debug(json.dumps(form.errors.as_json(), indent=2))
    
    # Log formset data and errors if exists
    if formset:
        logger.debug("Formset Information:")
        logger.debug(f"  Total Forms: {formset.total_form_count()}")
        logger.debug(f"  Initial Forms: {formset.initial_form_count()}")
        logger.debug(f"  Is Valid: {formset.is_valid()}")
        
        if not formset.is_valid():
            logger.debug("Formset Errors:")
            for i, form_errors in enumerate(formset.errors):
                if form_errors:
                    logger.debug(f"  Form {i} Errors:")
                    logger.debug(json.dumps(form_errors, indent=2))
            
            if formset.non_form_errors():
                logger.debug("Formset Non-Form Errors:")
                logger.debug(json.dumps(formset.non_form_errors(), indent=2))

class ExerciseListView(LoginRequiredMixin, ListView):
    model = Exercise
    template_name = 'workouts/exercise_list.html'
    context_object_name = 'exercises'

    def get_queryset(self):
        try:
            return Exercise.objects.filter(user=self.request.user)
        except Exception as e:
            logger.error(f"Error fetching exercises for user {self.request.user}: {str(e)}")
            messages.error(self.request, "Error loading exercises. Please try again.")
            return Exercise.objects.none()

class ExerciseCreateView(LoginRequiredMixin, CreateView):
    model = Exercise
    fields = ['name', 'description']
    template_name = 'workouts/exercise_form.html'
    success_url = reverse_lazy('workouts:exercise_list')

    def form_valid(self, form):
        try:
            logger.info(f"Creating exercise with data: {form.cleaned_data}")
            form.instance.user = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, 'Exercise created successfully!')
            return response
        except Exception as e:
            logger.error(f"Error creating exercise: {str(e)}", exc_info=True)
            messages.error(self.request, f"Error creating exercise: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.warning(f"Invalid exercise form submission: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

class ExerciseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Exercise
    fields = ['name', 'description']
    template_name = 'workouts/exercise_form.html'
    success_url = reverse_lazy('workouts:exercise_list')

    def test_func(self):
        exercise = self.get_object()
        return exercise.user == self.request.user

    def form_valid(self, form):
        try:
            logger.info(f"Updating exercise {self.object.id} with data: {form.cleaned_data}")
            response = super().form_valid(form)
            messages.success(self.request, 'Exercise updated successfully!')
            return response
        except Exception as e:
            logger.error(f"Error updating exercise {self.object.id}: {str(e)}", exc_info=True)
            messages.error(self.request, f"Error updating exercise: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.warning(f"Invalid exercise update form submission: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def handle_no_permission(self):
        logger.warning(f"Unauthorized access attempt to exercise {self.kwargs.get('pk')} by user {self.request.user}")
        messages.error(self.request, "You don't have permission to edit this exercise.")
        return redirect('workouts:exercise_list')

class ExerciseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Exercise
    template_name = 'workouts/exercise_confirm_delete.html'
    success_url = reverse_lazy('workouts:exercise_list')

    def test_func(self):
        exercise = self.get_object()
        return exercise.user == self.request.user

    def delete(self, request, *args, **kwargs):
        try:
            exercise = self.get_object()
            logger.info(f"Deleting exercise {exercise.id}")
            response = super().delete(request, *args, **kwargs)
            messages.success(self.request, 'Exercise deleted successfully!')
            return response
        except Exception as e:
            logger.error(f"Error deleting exercise {kwargs.get('pk')}: {str(e)}", exc_info=True)
            messages.error(self.request, f"Error deleting exercise: {str(e)}")
            return redirect('workouts:exercise_list')

    def handle_no_permission(self):
        logger.warning(f"Unauthorized delete attempt for exercise {self.kwargs.get('pk')} by user {self.request.user}")
        messages.error(self.request, "You don't have permission to delete this exercise.")
        return redirect('workouts:exercise_list')

class WorkoutListView(LoginRequiredMixin, ListView):
    model = Workout
    template_name = 'workouts/workout_list.html'
    context_object_name = 'workouts'

    def get_queryset(self):
        return Workout.objects.filter(user=self.request.user)

class WorkoutDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Workout
    template_name = 'workouts/workout_detail.html'
    context_object_name = 'workout'

    def test_func(self):
        workout = self.get_object()
        return workout.user == self.request.user

class WorkoutCreateView(LoginRequiredMixin, CreateView):
    model = Workout
    form_class = WorkoutForm
    template_name = 'workouts/workout_form.html'
    success_url = reverse_lazy('workouts:workout_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['exercises'] = WorkoutExerciseFormSet(self.request.POST)
            logger.debug("POST request - using submitted data for formset")
        else:
            data['exercises'] = WorkoutExerciseFormSet()
            # Set initial order for empty forms
            for i, form in enumerate(data['exercises'].forms):
                if not form.initial.get('order'):
                    form.initial['order'] = i + 1
                    logger.debug(f"Setting initial order {i + 1} for form {i}")
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        exercises = context['exercises']
        
        # Log debugging information
        debug_form_data(self.request, form, exercises)
        
        if not exercises.is_valid():
            logger.error("Exercise formset validation failed")
            for i, form_errors in enumerate(exercises.errors):
                if form_errors:
                    error_msg = f"Form {i} errors: {json.dumps(form_errors)}"
                    logger.error(error_msg)
                    messages.error(self.request, error_msg)
            return self.form_invalid(form)
            
        try:
            with transaction.atomic():
                # First save the workout
                form.instance.user = self.request.user
                self.object = form.save()
                logger.debug(f"Saved workout with ID: {self.object.id}")
                
                # Get valid forms (not marked for deletion)
                valid_forms = [f for f in exercises.forms if f.is_valid() and f.cleaned_data and not f.cleaned_data.get('DELETE')]
                
                if not valid_forms:
                    raise ValidationError("Please add at least one exercise to the workout.")
                
                # Now save the exercises with proper workout relationship
                for i, exercise_form in enumerate(valid_forms, start=1):
                    exercise = exercise_form.save(commit=False)
                    exercise.workout = self.object
                    exercise.order = i
                    exercise.save()
                    logger.debug(f"Saved exercise {exercise.exercise.name} with order {i}")
                
                # Verify exercises were saved
                saved_exercises = self.object.workoutexercise_set.count()
                logger.info(f"Saved {saved_exercises} exercises for workout {self.object.id}")
                
                if saved_exercises == 0:
                    raise ValidationError("No exercises were saved. Please try again.")
                    
                messages.success(self.request, 'Workout created successfully!')
                return super().form_valid(form)
                
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.exception("Unexpected error during workout creation")
            messages.error(self.request, f"An unexpected error occurred: {str(e)}")
            return self.form_invalid(form)
            
    def form_invalid(self, form):
        logger.error("Form validation failed")
        logger.error(f"Form errors: {json.dumps(form.errors.as_json(), indent=2)}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class WorkoutUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Workout
    form_class = WorkoutForm
    template_name = 'workouts/workout_form.html'
    success_url = reverse_lazy('workouts:workout_list')

    def test_func(self):
        workout = self.get_object()
        return workout.user == self.request.user

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            # If POST data exists, create formset with POST data
            formset = WorkoutExerciseFormSet(self.request.POST, instance=self.object)
            # We'll handle order in form_valid after validation
        else:
            # For GET requests, create formset with instance data
            formset = WorkoutExerciseFormSet(instance=self.object)
            # Set initial order for empty forms
            for i, form in enumerate(formset.forms):
                if not form.initial.get('order'):
                    form.initial['order'] = i + 1
        data['exercises'] = formset
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        exercises = context['exercises']
        
        # Log debugging information
        debug_form_data(self.request, form, exercises)
        
        if not exercises.is_valid():
            logger.error("Exercise formset validation failed")
            for i, form_errors in enumerate(exercises.errors):
                if form_errors:
                    error_msg = f"Form {i} errors: {json.dumps(form_errors)}"
                    logger.error(error_msg)
                    messages.error(self.request, error_msg)
            return self.form_invalid(form)
            
        try:
            with transaction.atomic():
                form.instance.user = self.request.user
                self.object = form.save()
                
                # Set order for forms after validation
                for i, form in enumerate(exercises.forms):
                    if form.is_valid() and form.cleaned_data and not form.cleaned_data.get('DELETE'):
                        form.instance.order = form.cleaned_data.get('order', i + 1)
                
                exercises.instance = self.object
                exercises.save()
                
                # Check if at least one exercise was added
                if not self.object.workoutexercise_set.exists():
                    raise ValidationError("Please add at least one exercise to the workout.")
                    
                messages.success(self.request, 'Workout updated successfully!')
                return super().form_valid(form)
                
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.exception("Unexpected error during workout update")
            messages.error(self.request, f"An unexpected error occurred: {str(e)}")
            return self.form_invalid(form)
            
    def form_invalid(self, form):
        logger.error("Form validation failed")
        logger.error(f"Form errors: {json.dumps(form.errors.as_json(), indent=2)}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class WorkoutDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Workout
    template_name = 'workouts/workout_confirm_delete.html'
    success_url = reverse_lazy('workouts:workout_list')

    def test_func(self):
        workout = self.get_object()
        return workout.user == self.request.user

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Workout deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required(login_url='accounts:login')
def index(request):
    return render(request, 'workouts/index.html', {
        'total_exercises': Exercise.objects.count(),
        'total_workouts': Workout.objects.filter(user=request.user).count(),
    })

class WorkoutSessionListView(LoginRequiredMixin, ListView):
    model = WorkoutSession
    template_name = 'workouts/session_list.html'
    context_object_name = 'sessions'

    def get_queryset(self):
        return WorkoutSession.objects.filter(user=self.request.user).order_by('-started_at')

@login_required
def start_workout_session(request):
    if request.method == 'POST':
        form = WorkoutSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.save()
            messages.success(request, 'Workout session started!')
            return redirect('workouts:session_detail', pk=session.pk)
    else:
        form = WorkoutSessionForm()
        # Only show workouts created by the user
        form.fields['workout'].queryset = Workout.objects.filter(user=request.user)
    
    return render(request, 'workouts/session_form.html', {'form': form})

class WorkoutSessionDetailView(LoginRequiredMixin, View):
    template_name = 'workouts/session_detail.html'

    def get_context_data(self, session):
        return {
            'session': session,
            'workout_exercises': session.workout.workoutexercise_set.all(),
            'performances': session.exerciseperformance_set.all().order_by('performed_at'),
            'form': ExercisePerformanceForm(workout_session=session)
        }

    def get(self, request, pk):
        session = get_object_or_404(WorkoutSession, pk=pk, user=request.user)
        return render(request, self.template_name, self.get_context_data(session))

    def post(self, request, pk):
        session = get_object_or_404(WorkoutSession, pk=pk, user=request.user)
        
        if 'finish_workout' in request.POST:
            if not session.finished_at:
                session.finished_at = timezone.now()
                session.save()
                messages.success(request, "Workout session completed!")
            return redirect('workouts:session_list')

        if session.finished_at:
            messages.error(request, "Cannot modify a finished workout session.")
            return redirect('workouts:session_detail', pk=pk)

        form = ExercisePerformanceForm(request.POST, workout_session=session)
        if form.is_valid():
            performance = form.save(commit=False)
            performance.workout_session = session
            performance.performed_at = timezone.now()
            
            # Get the last set number for this exercise in this session
            last_set = ExercisePerformance.objects.filter(
                workout_session=session,
                exercise=performance.exercise
            ).order_by('-set_number').first()
            
            performance.set_number = (last_set.set_number + 1) if last_set else 1
            performance.save()
            
            messages.success(request, "Set recorded successfully!")
            return redirect('workouts:session_detail', pk=pk)

        return render(request, self.template_name, {
            **self.get_context_data(session),
            'form': form
        })

class DeletePerformanceView(LoginRequiredMixin, View):
    def post(self, request, session_pk, performance_pk):
        session = get_object_or_404(WorkoutSession, pk=session_pk, user=request.user)
        if session.finished_at:
            messages.error(request, "Cannot modify a finished workout session.")
            return redirect('workouts:session_detail', pk=session_pk)

        performance = get_object_or_404(ExercisePerformance, pk=performance_pk, workout_session=session)
        performance.delete()
        messages.success(request, "Set deleted successfully!")
        return redirect('workouts:session_detail', pk=session_pk)

@login_required
def add_exercise_form(request):
    """HTMX view to add a new exercise form to the formset"""
    try:
        form_index = int(request.GET.get('form_index', 0))
        logger.debug(f"Adding exercise form with index: {form_index}")
        
        # Create a new formset with one form
        formset = WorkoutExerciseFormSet()
        empty_form = formset.empty_form
        
        # Update form index and prefix
        empty_form.prefix = empty_form.prefix.replace('__prefix__', str(form_index))
        
        # Set initial values
        empty_form.initial = {
            'order': form_index + 1,
            'suggested_sets': 3,
            'suggested_reps': 10
        }
        
        # Update widget attributes for each field
        for field_name, field in empty_form.fields.items():
            widget = field.widget
            widget_attrs = {
                'id': f'id_workoutexercise_set-{form_index}-{field_name}',
                'name': f'workoutexercise_set-{form_index}-{field_name}',
            }
            
            # Add any existing attributes
            widget_attrs.update(widget.attrs)
            
            # For order field, make it a hidden input with the value set
            if field_name == 'order':
                widget.input_type = 'hidden'
                widget_attrs['value'] = str(form_index + 1)
            
            widget.attrs = widget_attrs
            logger.debug(f"Field {field_name} attributes: {widget_attrs}")
        
        context = {
            'exercise_form': empty_form,
            'form_index': form_index,
        }
        
        # Add JavaScript to update the management form's TOTAL_FORMS
        context['update_total_forms'] = True
        context['new_total'] = form_index + 1
        
        return render(request, 'workouts/partials/exercise_form.html', context)
        
    except Exception as e:
        logger.exception("Error in add_exercise_form")
        return HttpResponse(f"Error adding exercise form: {str(e)}", status=500)

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
