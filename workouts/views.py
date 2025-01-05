from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from .models import Exercise, Workout, WorkoutExercise, WorkoutSession, ExercisePerformance
from .forms import (
    ExerciseForm, WorkoutForm, WorkoutExerciseFormSet,
    WorkoutSessionForm, ExercisePerformanceForm, ExercisePerformanceFormSet
)
from django.core.exceptions import ValidationError
import logging
import json

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
    login_url = 'accounts:login'

    def get_queryset(self):
        return Exercise.objects.filter(user=self.request.user)

class ExerciseCreateView(LoginRequiredMixin, CreateView):
    model = Exercise
    form_class = ExerciseForm
    template_name = 'workouts/exercise_form.html'
    success_url = reverse_lazy('workouts:exercise_list')
    login_url = 'accounts:login'

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Exercise created successfully!')
        return super().form_valid(form)

class ExerciseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Exercise
    form_class = ExerciseForm
    template_name = 'workouts/exercise_form.html'
    success_url = reverse_lazy('workouts:exercise_list')
    login_url = 'accounts:login'

    def test_func(self):
        exercise = self.get_object()
        return exercise.user == self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Exercise updated successfully!')
        return super().form_valid(form)

class ExerciseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Exercise
    template_name = 'workouts/exercise_confirm_delete.html'
    success_url = reverse_lazy('workouts:exercise_list')
    login_url = 'accounts:login'

    def test_func(self):
        exercise = self.get_object()
        return exercise.user == self.request.user

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Exercise deleted successfully!')
        return super().delete(request, *args, **kwargs)

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
        else:
            data['exercises'] = WorkoutExerciseFormSet()
            # Set initial order for empty forms
            for i, form in enumerate(data['exercises'].forms):
                if not form.initial.get('order'):
                    form.initial['order'] = i + 1
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
                
                if exercises.is_valid():
                    # Set order for forms after validation
                    for i, form in enumerate(exercises.forms):
                        if form.is_valid() and form.cleaned_data and not form.cleaned_data.get('DELETE'):
                            form.instance.order = form.cleaned_data.get('order', i + 1)
                    
                    exercises.instance = self.object
                    exercises.save()
                    
                    # Check if at least one exercise was added
                    if not self.object.workoutexercise_set.exists():
                        raise ValidationError("Please add at least one exercise to the workout.")
                        
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
        
        formset = WorkoutExerciseFormSet()
        empty_form = formset.empty_form
        
        # Log form generation details
        logger.debug(f"Empty form prefix before update: {empty_form.prefix}")
        
        # Update form index in the prefix
        empty_form.prefix = empty_form.prefix.replace('__prefix__', str(form_index))
        logger.debug(f"Empty form prefix after update: {empty_form.prefix}")
        
        # Set initial values including order
        empty_form.initial = {
            'order': form_index + 1,  # Set order to form_index + 1
            'suggested_sets': 3,  # Default values
            'suggested_reps': 10
        }
        logger.debug(f"Updated initial data: {empty_form.initial}")
        
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
        return render(request, 'workouts/partials/exercise_form.html', context)
        
    except Exception as e:
        logger.exception("Error in add_exercise_form")
        return HttpResponse(f"Error adding exercise form: {str(e)}", status=500)
