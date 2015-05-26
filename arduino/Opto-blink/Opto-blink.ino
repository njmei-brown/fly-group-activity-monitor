/* Opto-blink
 Code adapted from: http://www.arduino.cc/en/Tutorial/BlinkWithoutDelay
 Modifications by Nicholas Mei
 */

// Set pin number:
const int led_pin =  13;                // the number of the LED pin

// Variables that will change:
float desired_frequency = 1;            // Desired frequency of blink (Hz)
float desired_on_time = 5;              // Desired LED ON time for blink (in ms)
int led_state = LOW;                    // led_state used to set the LED
unsigned long previous_millis = 0;      // will store last time LED was updated
unsigned long millis_diff = 0;          
boolean run_blink = 0;
float interval = (1000/desired_frequency)-desired_on_time;           // interval at which to blink (milliseconds)

void setup() {  
  pinMode(led_pin, OUTPUT);
  Serial.begin(9600);
  // set the digital pin as output:      
}

void loop()
{
  // Check to see if Python has sent a serial message
  if(Serial.available() > 0) {
    // Arduino will expect serial messages in the following format: 'desired_freq,desired_on_time'
    String des_freq = Serial.readStringUntil(',');
    Serial.read();
    desired_on_time = Serial.parseFloat();
    desired_frequency = des_freq.toFloat();
    //update the interval
    if (desired_frequency == 0 || desired_on_time == 0) {
      run_blink = 0;    
      digitalWrite(led_pin, LOW); 
    }
    else {
      interval = (1000/desired_frequency)-desired_on_time; 
      run_blink = 1;
      digitalWrite(led_pin, LOW);
    }
  }
  unsigned long current_millis = millis();
  // Check if we're in LED blink mode or not
  if (run_blink == 1) {
    millis_diff = current_millis - previous_millis;
    // Check if we're in LED OFF state
    if(led_state == LOW){
      // Check if we have exceeded our off time interval
      if(millis_diff > interval) {
        // Save when you turn on the LED 
        previous_millis = current_millis;   
        led_state = HIGH;
        digitalWrite(led_pin, led_state);
        }   
    }
    // If not, we're in LED ON state
    else{
      if (millis_diff > desired_on_time){
        // Save when you turn off the LED
        previous_millis = current_millis;
        led_state = LOW;
        digitalWrite(led_pin, led_state); 
      }
    }      
  }
  // If we're not in LED blink mode we set the state to HIGH
  else {
    if (led_state == HIGH) {
      led_state = LOW;
      digitalWrite(led_pin, led_state);
    }
  }
}
