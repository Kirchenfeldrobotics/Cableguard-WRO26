# Cable Label Legend 
All cables have a label. 
The first two digits corresponds to an electronic component. 
The third digit corresponds to a specifc pin of such a component. 
## Generell: (add common gnd)
* GND: GND (common Ground)

## Components 
### 00 - Raspberry Pi 5 
* 0: GND
* 1: SDA 
* 2: SCL 
* 3: Vcc (3.3V) 
* 4: GND

### 01 - Motion Stepper Driver 
* 0: GND
* 1: GND
* 2: DIR
* 3: PUL 
* 4: GND 
* 5: Vcc (12V)

### 02 - Camera Stepper Driver
* 0: GND
* 1: GND
* 2: DIR
* 3: PUL 
* 4: GND 
* 5: Vcc (12V)

### 03 - Display 
* 0: GND 
* 1: VDD
* 2: SCK
* 3: SDA

### 04 - ToF Sensor 
* 0: Vcc
* 1: GND
* 2: SDA
* 3: SCL

### 05 - DC Step Down 
* 0: GND 
* 1: Vcc (12V)

### 06 - Battery 

### 07 - Button Red 
* 0: SIG 
* 1: GND (All buttons)

### 08 - Button White  
* 0: SIG

### 09 - Button Yellow
* 0: SIG

### 10 - Buzzer 
* 0: GND 
* 1: SIG

## Groups
Description: Groups are connected cables that from the same interface to have less cable mess to connect to the RPI 5.

