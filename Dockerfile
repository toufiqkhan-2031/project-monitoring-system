#Docker image that gives all required tools and libraries
FROM python:3.12-slim

#create a folder where the app will be stored
WORKDIR /app

#copy to requirement file
COPY requirements.txt .

#compaile the appplication code
RUN pip install --no-cache-dir -r requirements.txt

#copy the source code from host machine to your container
COPY . .

EXPOSE 5000

#run the application
CMD ["python","app.py"]

