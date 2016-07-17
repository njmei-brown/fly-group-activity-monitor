/* Opto-blink_and_Solenoids
 Code adapted from: http://www.arduino.cc/en/Tutorial/BlinkWithoutDelay
 Modifications by Nicholas Mei
 */

// Set pin numbers:
const int LED_PIN =  13;     // the number of the LED pin
const int SOL_PIN_1 = 3;     // the numbers for the solenoid pins
const int SOL_PIN_2 = 5;
const int SOL_PIN_3 = 6;
const int SOL_PIN_4 = 9;

const int NUM_FIELDS = 6;    //'desired_freq,desired_on_time,sol_1_status,sol_2_status,sol_3_status,sol_4_status'

// Variables that will change:
int field_indx = 0;
float values[NUM_FIELDS] = { 0 };       // Array to store values, initialize all to 0

float desired_frequency = 5;            // Desired frequency of blink (Hz)
float desired_on_time = 5;              // Desired LED ON time for blink (in ms)
int led_state = LOW;                    // led_state used to set the LED

//Note: using unsigned long will guarantee overflow proof code since we are taking 
//micros diff comparisons will be the equivalent to: (current_micros-previous_micros)% 4,294,967,295
unsigned long current_micros = 0;       // using unsigned long will guarantee overflow proof code since we are taking 
unsigned long previous_micros = 0;      // will store last time LED was updated
unsigned long micros_diff = 0;     
     
boolean run_blink = 0;
float blink_interval = (1000000/desired_frequency)-desired_on_time*1000;           // interval at which to blink (microseconds)

/*===================== Setup ==============================*/
void setup() {  
  //Set the digital pin as output: 
  pinMode(LED_PIN, OUTPUT);
  pinMode(SOL_PIN_1, OUTPUT);
  pinMode(SOL_PIN_2, OUTPUT);
  pinMode(SOL_PIN_3, OUTPUT);
  pinMode(SOL_PIN_4, OUTPUT);
  //Start serial comms and set baud rate to 115200
  Serial.begin(115200);  
  //We also don't want the arduino waiting for too long on serial reads before timing out
  Serial.setTimeout(2);
}

/*===================== Solenoid Update ==================== */
void update_solenoid(float on_status, int PIN){
  if (on_status == 1) {
    digitalWrite(PIN, HIGH);
  }
  else {
    digitalWrite(PIN, LOW);
  }
}

/*===================== Blink Loop ========================= */
void loop() {
  // Check to see if Python has sent a serial message
  if(Serial.available() > 0) {
    // Arduino will expect serial messages in the following format: 'desired_freq,desired_on_time,sol_1_status,sol_2_status,sol_3_status,sol_4_status'
    // Also possible that Arduino will only recieve 'desired_freq,desired_on_time'
    for (field_indx = 0; field_indx < NUM_FIELDS; field_indx++) {
      values[field_indx] = Serial.parseFloat();
    }            
    for(int i=0; i < field_indx; i++) {
      switch (i) {
        case 0:
          desired_frequency = values[i];
          break;
        case 1:
          desired_on_time = values[i];
          break;
        case 2:
          update_solenoid(values[i], SOL_PIN_1);
          break;
        case 3:
          update_solenoid(values[i], SOL_PIN_2);
          break;
        case 4:
          update_solenoid(values[i], SOL_PIN_3);
          break;
        case 5:
          update_solenoid(values[i], SOL_PIN_4);
          break;         
        }
      }
    field_indx = 0;
    //update the interval
    if (desired_frequency == 0 || desired_on_time == 0) {
      run_blink = 0;    
      led_state = LOW;
      digitalWrite(LED_PIN, led_state); 
    }
    else {
      blink_interval = (1000000/desired_frequency)-desired_on_time*1000; 
      run_blink = 1;
      led_state = LOW;
      digitalWrite(LED_PIN, led_state);
    }

    //Write back out the values that have been sent to indicate that communication was successful
    for (int j=0; j < NUM_FIELDS; j++) {
      Serial.print(values[j]);
      if (j < NUM_FIELDS-1) {
        Serial.print(",");   
      } 
    }
    //Write out the final newline character denoting end of communication after writeloop is done
    Serial.print("\n");
  }
  // Check if we're in LED blink mode or not
  if (run_blink == 1) {
    current_micros = micros();
    micros_diff = current_micros - previous_micros;
    
    // Check if we're in LED OFF state
    if(led_state == LOW){
      // Check if we have exceeded our off time interval
      if(micros_diff > blink_interval) {
        // Save when you turn on the LED 
        previous_micros = current_micros;   
        led_state = HIGH;
        digitalWrite(LED_PIN, led_state);
        }   
    }
    // If not, we're in LED ON state
    else{
      if (micros_diff > desired_on_time*1000){
        // Save when you turn off the LED
        previous_micros = current_micros;
        led_state = LOW;
        digitalWrite(LED_PIN, led_state); 
      }
    }      
  }
}

