# Getting started

## Dataset

- WISDM - Standardized dataset for wide-patterns.

      This dataset was created by Gary M. Weiss at Fordham University's WISDM (Wireless Sensor Data Mining) Lab and donated to 
      the UCI Machine Learning Repository (2019). It contains raw accelerometer and gyroscope time-series data 
      from both a smartphone and a smartwatch, with the watch component being the LG G Watch running Android Wear 1.5, worn on
      the dominant hand of each subject.
      51 subjects, each performing 18 activities for 3 minutes each, yielding 54 minutes of data per subject.
      
      Non-hand-oriented:
         Walking (A), Jogging (B), Stairs (C), Standing (E), Kicking (M)
      
      Hand-oriented (general):
         Typing (F), Brushing Teeth (G), Dribbling (P), Playing Catch (O), Writing (Q), Clapping (R), Folding Clothes (S)
      
      Hand-oriented (eating):
         Eating Soup (H), Eating Chips (I), Eating Pasta (J), Drinking from Cup (K), Eating Sandwich (L)


- M5-WATCH Stick C Plus based dataset. 

      Activity chosen for this project:
        - Walking
        - Eating 
        - Typing
        - Sedentary (standing and sitting)

> 6-Axis IMU (MPU6886)

<p align="center">
      <img width="400" height="500" alt="image" src="https://github.com/user-attachments/assets/b0de1805-d42e-4e03-b09d-33931e227cc9"/>      
</p>

- Accelerometer - points to be considered for proper $\pm g$ selection :
  
  1. The __MPU-6886__ features a 16-bit (-32,768 to +32,767) Analog-to-Digital Converter (ADC) for each axis (X, Y, Z), meaning the sensor has exactly 65,536 total steps to describe the physical acceleration it feels.
  2. The __Full Scale Range - FSR__ is the maximum physical acceleration the sensor can measure before it "clips" or "saturates" (maxes out). The MPU-6886 has a programmable FSR with four options:
        - ±2g
        - ±4g
        - ±8g (M5StickC Plus default value of 'g' via M5Stack library)
        - ±16g
  3. Lower g values can help capture incredibly fine, detailed nuances of gentle movements. While higher g values are used to capture movements such as falling and activities like shock.
  4. Sensitivity (LSB/g), the scale Factor answers the question - "How many raw steps make up 1g of physical acceleration?" which is given by __Sensitivity = $\frac{32768}{FSR Max}$__.

     example: For $\pm 8g$ --> Sensitivity (LSB/g) = 4,096 (LSB/g) --> meaning at $\pm 8g$ FSR: 1 step = 1 / 4096 = 0.000244 g (the resolution) !!

   __"These should be kept in mind while selecting or changing the firmware(library functions) for g values to capture an activity"__
      
> Misc

- Power On: Press the reset button for at least 2 seconds
- Power Off: Press the reset button for at least 6 seconds

