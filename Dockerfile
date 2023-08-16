FROM ubuntu:latest
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install locales tzdata \
    python3-pip python3-cffi python3-brotli libpango-1.0-0 \
    libpangoft2-1.0-0 fonts-noto -y

RUN pip install fastapi uvicorn icalendar requests weasyprint
ADD ./main.py /main.py
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
