FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=FitPaw.settings

EXPOSE 8000

CMD ["python", "FitPaw/manage.py", "runserver", "0.0.0.0:8000"]