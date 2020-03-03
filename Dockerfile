FROM registry.gitlab.com/chariot-h2020/chariot_base:latest

VOLUME ["/usr/src/app"]
WORKDIR /usr/src/app

# Bundle app source
COPY . .

RUN pip install falcon-jsonify && python setup.py install

CMD ["python", "./chariot_health_service/check.py"]