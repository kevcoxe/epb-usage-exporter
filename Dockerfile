FROM python

WORKDIR /app

COPY requirements.txt .
COPY main.py .

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
