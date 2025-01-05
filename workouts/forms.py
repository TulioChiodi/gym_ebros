from django import forms
from .models import Exercise, Workout, WorkoutExercise, WorkoutSession, ExercisePerformance
from django.db import models

class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['name', 'description']

class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class WorkoutExerciseForm(forms.ModelForm):
    class Meta:
        model = WorkoutExercise
        fields = ['exercise', 'suggested_sets', 'suggested_reps', 'notes', 'order']
        widgets = {
            'exercise': forms.Select(attrs={'class': 'form-control'}),
            'suggested_sets': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'suggested_reps': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
            'order': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make exercise field required
        self.fields['exercise'].required = True
        self.fields['suggested_sets'].required = True
        self.fields['suggested_reps'].required = True
        
        # Set initial values for new forms
        if not self.instance.pk and not self.data:
            self.fields['suggested_sets'].initial = 3
            self.fields['suggested_reps'].initial = 10
            
            try:
                if hasattr(self.instance, 'workout') and self.instance.workout:
                    # Get the current max order value
                    max_order = WorkoutExercise.objects.filter(
                        workout=self.instance.workout
                    ).aggregate(models.Max('order'))['order__max']
                    # Set the order to max + 1 (or 1 if no exercises exist)
                    self.initial['order'] = (max_order or 0) + 1
                else:
                    # If there's no workout yet, get the form index from prefix
                    prefix = self.prefix or ''
                    try:
                        index = int(prefix.split('-')[1]) if '-' in prefix else 0
                        self.initial['order'] = index + 1
                    except (IndexError, ValueError):
                        self.initial['order'] = 1
            except (AttributeError, WorkoutExercise.workout.RelatedObjectDoesNotExist):
                self.initial['order'] = 1

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('order'):
            # If order is not set, try to get it from the form prefix
            prefix = self.prefix or ''
            try:
                index = int(prefix.split('-')[1]) if '-' in prefix else 0
                cleaned_data['order'] = index + 1
            except (IndexError, ValueError):
                cleaned_data['order'] = 1
        return cleaned_data

class WorkoutSessionForm(forms.ModelForm):
    class Meta:
        model = WorkoutSession
        fields = ['workout', 'notes']
        widgets = {
            'workout': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
        }

class ExercisePerformanceForm(forms.ModelForm):
    class Meta:
        model = ExercisePerformance
        fields = ['exercise', 'reps', 'weight', 'notes']
        widgets = {
            'exercise': forms.Select(attrs={'class': 'form-select'}),
            'reps': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.5'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
        }

    def __init__(self, *args, **kwargs):
        workout_session = kwargs.pop('workout_session', None)
        super().__init__(*args, **kwargs)
        if workout_session:
            # Only show exercises from the current workout, ordered by their order in the workout
            self.fields['exercise'].queryset = Exercise.objects.filter(
                workoutexercise__workout=workout_session.workout
            ).distinct().order_by('workoutexercise__order')
        self.fields['notes'].required = False

WorkoutExerciseFormSet = forms.inlineformset_factory(
    Workout, WorkoutExercise,
    form=WorkoutExerciseForm,
    fields=['exercise', 'suggested_sets', 'suggested_reps', 'notes', 'order'],
    extra=1,
    can_delete=True,
    widgets={
        'exercise': forms.Select(attrs={'class': 'form-control'}),
        'suggested_sets': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        'suggested_reps': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
        'order': forms.HiddenInput(attrs={'class': 'exercise-order'}),
    }
)

ExercisePerformanceFormSet = forms.inlineformset_factory(
    WorkoutSession, ExercisePerformance,
    form=ExercisePerformanceForm,
    extra=1,
    can_delete=True
) 