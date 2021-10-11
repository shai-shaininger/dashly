FROM python:3.8
LABEL maintainer "shai shaininger <dummy@host.com>"
WORKDIR /code
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir dash pandas dash-bootstrap-components
# COPY ./ ./
EXPOSE 8050
# CMD ["python", "./app.py"]