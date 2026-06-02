# AI-Based Real-Time Student Engagement Detection System

This is the web-based version of the project. Students do not install Python, TensorFlow, OpenCV, or project files. They open the website, log in, allow browser camera access, and the backend predicts engagement using the trained TensorFlow model.

## Local Run

```cmd
python -m pip install -r requirements.txt
python app.py
```

Open:

```text
http://localhost:5000
```

Admin login:

```text
User ID: admin
Password: admin123
```

## Render Deployment

1. Push this folder to GitHub.
2. Create a new Render Web Service.
3. Connect the GitHub repository.
4. Use:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

Students open the Render HTTPS website link, log in, and allow camera permission.

## Important Files

- `app.py` - Flask website, prediction API, authentication, SQLite database
- `templates/` - Login, student dashboard, admin dashboard
- `static/` - CSS and browser camera JavaScript
- `models/engagement_model.h5` - trained TensorFlow model
- `models/class_names.json` - class label order
