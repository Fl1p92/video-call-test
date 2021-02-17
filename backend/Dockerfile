# Use an official Python runtime as a parent image
FROM python:3.8.7

# Set the envs
ENV PROJECT_ROOT /srv/video-call-test/backend
ENV PYTHONPATH /srv/video-call-test:$PYTHONPATH
ENV PYTHONSTARTUP $PROJECT_ROOT/.python_startup.py

# Set the working directory
WORKDIR $PROJECT_ROOT

# Copy file of project dependencies
COPY requirements.in $PROJECT_ROOT/requirements.in

# Compile and install any needed packages specified in requirements.in
RUN pip install --upgrade pip
RUN pip install pip-tools
RUN pip-compile requirements.in --quiet
RUN pip-sync requirements.txt --pip-args '--no-cache-dir'
