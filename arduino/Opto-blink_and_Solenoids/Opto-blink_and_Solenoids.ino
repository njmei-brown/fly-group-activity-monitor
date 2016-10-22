/* Opto-blink_and_Solenoids
 Code adapted from: http://www.arduino.cc/en/Tutorial/BlinkWithoutDelay
 Modifications by Nicholas Mei
 Version 3.0 Updated 10/20/2016
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
const byte SOL_PIN_5 = 10;
const byte SOL_PIN_6 = 11;

//Variables for serial communication message storage
boolean ser_msg_received = false;

const byte num_chars = 40;
char received_chars[num_chars];

float led_values[2] = {0}; //float array to store led freq and dur values, initialize all to 0
int sol_values[6] = {0}; //int array to store solenoid states, initialize all to 0

//Variables for LED blinking and timing
boolean run_blink = 0;

float desired_frequency = 5;            // Desired frequency of blink (Hz)
float desired_on_time = 5;              // Desired LED ON time for blink (in ms)
float blink_interval = (1000000/desired_frequency)-desired_on_time*1000;           // interval at which to blink (microseconds)

//Note: using unsigned long will guarantee overflow proof code since we are taking 
//micros diff comparisons will be the equivalent to: (current_micros-previous_micros)% 4,294,967,295
unsigned long current_micros = 0;       // using unsigned long will guarantee overflow proof code since we are taking 
unsigned long previous_micros = 0;      // will store last time LED was updated
unsigned long micros_diff = 0;     

/*===================== Setup ==============================*/
void setup() {  
  //Set the digital pin as output:   
  pinAsOutput(LED_PIN);
  pinAsOutput(SOL_PIN_1);
  pinAsOutput(SOL_PIN_2);
  pinAsOutput(SOL_PIN_3);
  pinAsOutput(SOL_PIN_4);
  pinAsOutput(SOL_PIN_5);
  pinAsOutput(SOL_PIN_6);
  //Start serial comms and set baud rate to 250000
  Serial.begin(250000);  
  //We also don't want the arduino waiting for too long on serial reads before timing out
  //Wait 2 milliseconds before timing out
  Serial.setTimeout(2);
}

/*===================== Solenoid Update ====================*/
void update_solenoid(int on_status, byte PIN){
  if (on_status == 1) {
    digitalHigh(PIN);
  }
  else {
    digitalLow(PIN);
  }
}

/*===================== Serial Receive =========================*/
void serial_recv(){  
  static boolean receiving_msg = false;
  static byte indx = 0;
  
  char msg_start = '[';
  char msg_end = ']';
  char msg;

  while (Serial.available() > 0 && ser_msg_received == false){
    msg = Serial.read();
    if (receiving_msg == true){
      if (msg != msg_end){
        received_chars[indx] = msg;
        indx++;
        
        //prevent accidental overflow of our received_chars array
        if (indx >= num_chars){
          indx = num_chars - 1;
        }
      }
      //we got the message termination character!
      else {
        received_chars[indx] = '\0'; //add null terminator to end of char array
        receiving_msg = false;
        indx = 0;
        ser_msg_received = true;
      }
    }
    else if ( msg == msg_start) {
      receiving_msg = true;
    }
  }
}

/*===================== Parse Serial Data =========================*/
void parse_ser_data() {      // split the data into its parts
  int i = 0;

  //iterate through received character array return tokens separated by ","
  for (char *token = strtok(received_chars,","); token != NULL; token = strtok(NULL, ",")) {
    switch (i) {
      case 0:
        led_values[0] = atof(token);
        desired_frequency = led_values[0];
        break;
      case 1:
        led_values[1] = atof(token);
        desired_on_time = led_values[1];
        break;
      case 2:
        sol_values[0] = atoi(token);
        update_solenoid(sol_values[0], SOL_PIN_1);
        break;
      case 3:
        sol_values[1] = atoi(token);
        update_solenoid(sol_values[1], SOL_PIN_2);
        break;
      case 4:
        sol_values[2] = atoi(token);
        update_solenoid(sol_values[2], SOL_PIN_3);
        break;
      case 5:
        sol_values[3] = atoi(token);
        update_solenoid(sol_values[3], SOL_PIN_4);
        break;       
      case 6:
        sol_values[4] = atoi(token);
        update_solenoid(sol_values[4], SOL_PIN_5);
        break;   
      case 7:
        sol_values[5] = atoi(token);
        update_solenoid(sol_values[5], SOL_PIN_6);
        break;    
    } 
    i++;
  }
}

/*===================== Update Blink Parameters =========================*/
void update_blink_params(){
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
}

/*===================== Confirm Parsed Data =========================*/
void confirm_parsed_data() {

    //Write back out the values that have been sent to indicate that communication was successful
    for (int j=0; j < 2; j++) {
      Serial.print(led_values[j]);
      Serial.print(",");  
    }
    for (int k=0; k < 6; k++) {
      Serial.print(sol_values[k]);
      if (k < 5) {
        Serial.print(",");   
      } 
    }
    
    //Write out the final newline character denoting end of communication after writeloop is done
    Serial.print("\n");
}

/*===================== Blink Loop =========================*/
void loop() {
  
  serial_recv();
  
  if (ser_msg_received == true) {
        parse_ser_data();
        confirm_parsed_data();
        update_blink_params();
        ser_msg_received = false;
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

