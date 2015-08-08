/* Opto-blink
 Code adapted from: http://www.arduino.cc/en/Tutorial/BlinkWithoutDelay
 Modifications by Nicholas Mei
 */
/*===================== Variables =========================*/
// Set pin number:
const int led_pin =  13;                  // the number of the LED pin

// Variables that will change:
float desired_frequency = 5;              // Desired frequency of blink (Hz)
float desired_on_time = 5;                // Desired LED ON time for blink (in ms)
int led_state = LOW;                      // led_state used to set the LED
unsigned long current_micros = micros();
unsigned long previous_micros = 0;        // will store last time LED was updated
unsigned long micros_diff = 0;          
boolean run_blink = 0;
float interval = (1000000/desired_frequency)-desired_on_time*1000;           // interval at which to blink (microseconds)

/*===================== Setup ==============================*/
void setup() {  
  Serial.begin(115200);
  Serial.setTimeout(5);   //set a serial read timeout of 5 ms so that we don't get long delays before starting blinking
  // set the digital pin as output:   
  pinMode(led_pin, OUTPUT);  
}
/*===================== Blink Loop ========================= */
void loop()
{
  current_micros = micros();
  micros_diff = current_micros - previous_micros;
  
  // Check to see if Python has sent a serial message
  if(Serial.available() > 0 && led_state == LOW) {
    // Arduino will expect serial messages in the following format: 'desired_freq,desired_on_time'
    String des_freq = Serial.readStringUntil(',');
    Serial.read();
    desired_on_time = Serial.parseFloat();
    desired_frequency = des_freq.toFloat();
    //update the interval
    if (desired_frequency == 0 || desired_on_time == 0) {
      run_blink = 0;    
      led_state = LOW;
      digitalWrite(led_pin, led_state); 
      Serial.write("OFF");
    }
    else {
      interval = (1000000/desired_frequency)-desired_on_time*1000; 
      run_blink = 1;
      current_micros = micros();
      previous_micros = 0;
      micros_diff = 0;
      led_state = LOW;
      digitalWrite(led_pin, led_state);
      Serial.write("ON");
    }
  }
  // Check if we're in LED blink mode or not
  if (run_blink == 1) {
    // Check if we're in LED OFF state
    if(led_state == LOW){
      // Check if we have exceeded our off time interval
      if(micros_diff > interval) {
        // Save when you turn on the LED 
        previous_micros = current_micros;   
        led_state = HIGH;
        digitalWrite(led_pin, led_state);
        }   
    }
    // If not, we're in LED ON state
    else{
      if (micros_diff > desired_on_time*1000){
        // Save when you turn off the LED
        previous_micros = current_micros;
        led_state = LOW;
        digitalWrite(led_pin, led_state); 
      }
    }      
  }
}
