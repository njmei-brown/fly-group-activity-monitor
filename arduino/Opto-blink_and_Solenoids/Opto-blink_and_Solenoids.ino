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
    
    // Check if we're in LED OFF state
    if(led_state == LOW){
      // Check if we have exceeded our off time interval
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

