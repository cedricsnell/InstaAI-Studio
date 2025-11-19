@echo off
echo Starting InstaAI Studio Web Server...
echo.
echo Access the web interface at: http://localhost:8000
echo API documentation at: http://localhost:8000/docs
echo.
echo Default login: admin / admin123
echo.
echo Press Ctrl+C to stop the server
echo.

cd src\web
python app.py
