FROM alpine:3.20

WORKDIR /app

COPY docker/services/run-service.sh /app/run-service.sh

RUN chmod +x /app/run-service.sh

CMD ["/app/run-service.sh"]
