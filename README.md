# Gym Ebros

A Django-based workout tracking application that helps users manage their exercises and workout routines.

## Features

- User Authentication (Login, Signup, Logout)
- Exercise Management
- Workout Tracking
- Bootstrap UI
- HTMX Integration

## Tech Stack

- Python 3.10
- Django 5.1.4
- PostgreSQL
- Bootstrap 5
- HTMX

## Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/gym_ebros.git
cd gym_ebros
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install django psycopg2-binary django-htmx
```

4. Configure PostgreSQL:
- Create a database named 'gym_ebros'
- Update database settings in settings.py if needed

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

Visit http://localhost:8000 to see the application.

## Project Structure

- `accounts/`: User authentication app
- `workouts/`: Main application for exercise and workout management
- `templates/`: HTML templates
- `static/`: Static files (CSS, JS, images)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 