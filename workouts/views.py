from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import Exercise, Workout, WorkoutExercise, WorkoutSession, ExercisePerformance
from .forms import (
    ExerciseForm, WorkoutForm, WorkoutExerciseFormSet,
    WorkoutSessionForm, ExercisePerformanceForm, ExercisePerformanceFormSet
)

class ExerciseListView(LoginRequiredMixin, ListView):
    model = Exercise
    template_name = 'workouts/exercise_list.html'
    context_object_name = 'exercises'
    login_url = 'accounts:login'

class ExerciseCreateView(LoginRequiredMixin, CreateView):
    model = Exercise
    form_class = ExerciseForm
    template_name = 'workouts/exercise_form.html'
    success_url = reverse_lazy('workouts:exercise_list')
    login_url = 'accounts:login'

    def form_valid(self, form):
        messages.success(self.request, 'Exercise created successfully!')
        return super().form_valid(form)

class ExerciseUpdateView(LoginRequiredMixin, UpdateView):
    model = Exercise
    form_class = ExerciseForm
    template_name = 'workouts/exercise_form.html'
    success_url = reverse_lazy('workouts:exercise_list')
    login_url = 'accounts:login'

    def form_valid(self, form):
        messages.success(self.request, 'Exercise updated successfully!')
        return super().form_valid(form)

class ExerciseDeleteView(LoginRequiredMixin, DeleteView):
    model = Exercise
    template_name = 'workouts/exercise_confirm_delete.html'
    success_url = reverse_lazy('workouts:exercise_list')
    login_url = 'accounts:login'

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
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        exercises = context['exercises']
        with transaction.atomic():
            form.instance.user = self.request.user
            self.object = form.save()
            if exercises.is_valid():
                exercises.instance = self.object
                exercises.save()
        messages.success(self.request, 'Workout created successfully!')
        return super().form_valid(form)

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
            data['exercises'] = WorkoutExerciseFormSet(self.request.POST, instance=self.object)
        else:
            data['exercises'] = WorkoutExerciseFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        exercises = context['exercises']
        with transaction.atomic():
            form.instance.user = self.request.user
            self.object = form.save()
            if exercises.is_valid():
                exercises.instance = self.object
                exercises.save()
        messages.success(self.request, 'Workout updated successfully!')
        return super().form_valid(form)

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
            'performances': session.exerciseperformance_set.all().order_by('created_at'),
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
            return redirect('workouts:session_list')

        if session.finished_at:
            messages.error(request, "Cannot modify a finished workout session.")
            return redirect('workouts:session_detail', pk=pk)

        form = ExercisePerformanceForm(request.POST, workout_session=session)
        if form.is_valid():
            performance = form.save(commit=False)
            performance.workout_session = session
            
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
