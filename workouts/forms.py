from django import forms
from .models import Exercise, Workout, WorkoutExercise, WorkoutSession, ExercisePerformance

class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['name', 'description', 'target_muscle']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'target_muscle': forms.TextInput(attrs={'class': 'form-control'}),
        }

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
            # Only show exercises from the current workout
            self.fields['exercise'].queryset = Exercise.objects.filter(
                workoutexercise__workout=workout_session.workout
            )
        self.fields['notes'].required = False

WorkoutExerciseFormSet = forms.inlineformset_factory(
    Workout, WorkoutExercise,
    form=WorkoutExerciseForm,
    extra=1,
    can_delete=True
)

ExercisePerformanceFormSet = forms.inlineformset_factory(
    WorkoutSession, ExercisePerformance,
    form=ExercisePerformanceForm,
    extra=1,
    can_delete=True
) 