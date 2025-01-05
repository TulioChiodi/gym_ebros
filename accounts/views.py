from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.urls import reverse_lazy
from django.views.generic import CreateView, View
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from .forms import CustomUserCreationForm

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    
    def get_success_url(self):
        return reverse_lazy('workouts:index')

    def form_valid(self, form):
        # Save the user first
        user = form.save()
        # Log the user in
        login(self.request, user)
        messages.success(self.request, 'Account created successfully!')
        return redirect(self.get_success_url())

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('workouts:index')
    
    def form_valid(self, form):
        messages.success(self.request, 'Logged in successfully!')
        return super().form_valid(form)

class CustomLogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.success(request, 'You have been logged out successfully.')
        return redirect('workouts:index')
