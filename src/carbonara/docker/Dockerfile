# One image per stack, built from that stack's directory as the context.
# The image holds dependencies only. carbonara mounts the script at run time,
# the way a venv holds dependencies and the script comes from the package.
ARG PYTHON
FROM python:${PYTHON}-slim
ARG REQUIREMENTS
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY ${REQUIREMENTS} /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
WORKDIR /kitchen
