from django import forms
from django.contrib.auth.models import User
from django.db import models
from .models import Exercise, Workout, WorkoutExercise, WorkoutSession, ExercisePerformance, SharedWorkout

class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
        fields = ['workout']
        widgets = {
            'workout': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'workout' in self.fields:
            self.fields['workout'].label_from_instance = self.workout_label_from_instance

    @staticmethod
    def workout_label_from_instance(obj):
        if hasattr(obj, 'sharedworkout_set') and obj.sharedworkout_set.exists():
            return f"{obj.name} (Shared by {obj.user.username})"
        return obj.name

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

class WorkoutShareForm(forms.ModelForm):
    email = forms.EmailField(
        help_text="Enter the email of the user you want to share this workout with",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    can_edit = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Allow the user to edit this workout",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = SharedWorkout
        fields = ['can_edit']

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("No user found with this email address")
        return email

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