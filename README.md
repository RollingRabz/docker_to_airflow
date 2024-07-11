# Running Airflow in docker Workshop
This workshop will follow [Running Airflow in Docker](https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html)
The other necessary file can be found in the folder

Start with building the new container image with specified requirements.
```
docker-compose build
```

First initialization of Airflow:
```
docker-compose up airflow-init
```

Then, start all containers:
```
docker-compose up -d
```
The dag file contains 3 jobs which are 
1. Get data from the database
2. Get data from API
3. Merge the above data and transform price currency from US dollar to Thai baht
