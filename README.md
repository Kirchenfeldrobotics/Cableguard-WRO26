# Cableguard-WRO26
Cableguard is an automated rope inspection robot. This project is part of the World Robot Olympiad Future Innovators Category.

# Goal with Tech-Stack:
* Cable Inspection => hall sensor array with Kalman filter => Hall sensor connected to RPI 4/5
* Driving => Stepper Motor Nema 23 Steppers
* Connection => SIM Module, self-hosted fast-api server, Webapp (selfhosted with pw) => Sim card, sim module connected to RPI 4/5, selfhosted server
* Webapp => Representation of the data, rope quality score (calculate), presumned stability => algorithm (only software, maybe extern GenAI implementation)
* Hinge mechanism => robot opens that it can be put onto a rope => Servo
* IMU => measurement for pilow movement ect. => Adafruit BNO055

# Electronic Components
* RPI 4/5
* Hall Sensor (at least 8)
* Servo
* Sim Card module
* selfhosted Server
* Nema 23 Stepper Motors$
* Adafruit BNO055

