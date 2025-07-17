# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the project definition file
COPY pyproject.toml .

# Install dependencies. We don't need test dependencies in production.
# The --no-cache-dir option keeps the image size smaller.
RUN pip install --no-cache-dir .

# Copy the rest of the application code into the container
COPY ./fpl_agent ./fpl_agent

# Copy the .env file
COPY .env .

# Tell Docker that the container will listen on this port at runtime
EXPOSE 8080

# Define the command to run your application.
# We use 'adk web' to run the agent as a web service.
# --host 0.0.0.0 makes it accessible from outside the container.
CMD ["adk", "web", "fpl_agent", "--host", "0.0.0.0", "--port", "8080"]