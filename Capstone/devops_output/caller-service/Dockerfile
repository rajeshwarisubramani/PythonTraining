FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY app.py ./

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application using gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

# Notes:
# - The `--no-cache-dir` option is used with pip to prevent caching of the installed packages, reducing the image size.
# - Gunicorn is configured to use 4 worker processes (`-w 4`) for handling requests, which can be adjusted based on the server's CPU capabilities.
# - The application is bound to all network interfaces on port 5000 (`-b 0.0.0.0:5000`).
# - The `app:app` specifies the module and application instance to run, assuming `app.py` contains the Flask app instance named `app`.