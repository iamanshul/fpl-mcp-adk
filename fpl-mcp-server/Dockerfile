#Dockerfile

#--- Build Stage ---
# Use a full Python image to build dependencies. This stage has build tools.
FROM python:3.12-slim as builder
WORKDIR /app

COPY requirements.txt .

# Create a "wheelhouse" for our dependencies. This pre-compiles them.
# This makes the final image build faster and more reliable.
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# --- Final Stage ---
# Use a slim image for the final container to keep it small.
FROM python:3.12-slim

WORKDIR /app

# Copy the pre-built wheels from the builder stage
COPY --from=builder /wheels /wheels
# Copy the requirements file again
COPY requirements.txt .

# Install dependencies from the local wheels, which avoids hitting the network again.
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Copy the application code into the final image
COPY ./app ./app

# Expose the port the app will run on. Cloud Run expects 8080 by default.
EXPOSE 8080

# Command to run the application using Uvicorn.
# The host 0.0.0.0 is required to accept connections from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

