FROM postgres:17.2

ENV POSTGRES_USER=user
ENV POSTGRES_PASSWORD=password
ENV POSTGRES_DB=activity_tracker_db

COPY init.sql /docker-entrypoint-initdb.d/

EXPOSE 5432