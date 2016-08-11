/* Opto-blink_and_Solenoids
 Code adapted from: http://www.arduino.cc/en/Tutorial/BlinkWithoutDelay
 Modifications by Nicholas Mei
 Version 2.0 Updated 8/11/2016
 */

//Fast Pin operations using port registers
//Code from: http://masteringarduino.blogspot.com/2013/10/fastest-and-smallest-digitalread-and.html

#define portOfPin(P)\
  (((P)>=0&&(P)<8)?&PORTD:(((P)>7&&(P)<14)?&PORTB:&PORTC)) //If Pin # is >= 0 and < 8 return PORTD address, otherwise if Pin # is greater than 7 and less than 14 return PORTB, otherwise return PORTC
#define ddrOfPin(P)\
  (((P)>=0&&(P)<8)?&DDRD:(((P)>7&&(P)<14)?&DDRB:&DDRC))
#define pinOfPin(P)\
  (((P)>=0&&(P)<8)?&PIND:(((P)>7&&(P)<14)?&PINB:&PINC))
#define pinIndex(P)((uint8_t)(P>13?P-14:P&7))
#define pinMask(P)((uint8_t)(1<<pinIndex(P)))

#define pinAsInput(P) *(ddrOfPin(P))&=~pinMask(P)
#define pinAsInputPullUp(P) *(ddrOfPin(P))&=~pinMask(P);digitalHigh(P)
#define pinAsOutput(P) *(ddrOfPin(P))|=pinMask(P)
#define digitalLow(P) *(portOfPin(P))&=~pinMask(P)
#define digitalHigh(P) *(portOfPin(P))|=pinMask(P)
#define isHigh(P)((*(pinOfPin(P))& pinMask(P))>0)
#define isLow(P)((*(pinOfPin(P))& pinMask(P))==0)
#define digitalState(P)((uint8_t)isHigh(P))

//Set pin numbers
const byte LED_PIN = 13;
const byte SOL_PIN_1 = 3;
const byte SOL_PIN_2 = 5;
const byte SOL_PIN_3 = 6;
const byte SOL_PIN_4 = 9;

const int NUM_FIELDS = 6;    //'desired_freq,desired_on_time,sol_1_status,sol_2_status,sol_3_status,sol_4_status'

// Variables that will change:
int field_indx = 0;
float values[NUM_FIELDS] = { 0 };       // Array to store values, initialize all to 0

float desired_frequency = 5;            // Desired frequency of blink (Hz)
float desired_on_time = 5;              // Desired LED ON time for blink (in ms)

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
  pinAsOutput(LED_PIN);
  pinAsOutput(SOL_PIN_1);
  pinAsOutput(SOL_PIN_2);
  pinAsOutput(SOL_PIN_3);
  pinAsOutput(SOL_PIN_4);
  //Start serial comms and set baud rate to 115200
  Serial.begin(250000);  
  //We also don't want the arduino waiting for too long on serial reads before timing out
  //Wait 2 milleseconds before timing out
  Serial.setTimeout(2);
}

/*===================== Solenoid Update ==================== */
void update_solenoid(float on_status, byte PIN){
  if (on_status == 1) {
    digitalHigh(PIN);
  }
  else {
    digitalLow(PIN);
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
      digitalLow(LED_PIN);
    }
    else {
      blink_interval = (1000000/desired_frequency)-desired_on_time*1000; 
      run_blink = 1;
      digitalLow(LED_PIN);
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
    if( isLow( LED_PIN ) ){
      // Check if we have exceeded our off time interval
      if(micros_diff > blink_interval) {
        // Save when you turn on the LED 
        previous_micros = current_micros;   
        digitalHigh(LED_PIN);
        }   
    }
    // If not, we're in LED ON state
    else{
      if (micros_diff > desired_on_time*1000){
        // Save when you turn off the LED
        previous_micros = current_micros;
        digitalLow(LED_PIN);
      }
    }      
  }
}

