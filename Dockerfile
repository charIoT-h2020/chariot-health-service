FROM python:3.6-alpine
VOLUME ["/usr/src/app"]
WORKDIR /usr/src/app

# Bundle app source
COPY . .

RUN apk add gnupg gcc g++ make python3-dev libffi-dev openssl-dev gmp-dev && pip install falcon-jsonify gunicorn pytest && python setup.py install

CMD ["python", "./chariot_health_service/check.py"]