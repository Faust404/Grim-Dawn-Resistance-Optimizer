FROM python:3.11.9

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies if needed (uncomment if required)
# RUN apt-get update && apt-get install -y build-essential

# Copy requirements separately for caching
COPY requirements.txt /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the whole project into the container
COPY . /app/

# Expose port 5000 for Gunicorn
EXPOSE 5000

# Run Gunicorn as the main process
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "web.app:app"]