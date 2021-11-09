/*
 * A simple example to interface with rdm6300 rfid reader.
 *
 * Connect the rdm6300 to VCC=5V, GND=GND, TX=any GPIO (this case GPIO-10)
 * Note that the rdm6300's TX line is 3.3V level,
 * so it's safe to use with both AVR* and ESP* microcontrollers.

 * Arad Eizen (https://github.com/arduino12).
 * Edited by Andy Hegemann
 */

#include <rdm6300.h>

#define RDM6300_RX_PIN 10 


Rdm6300 rdm6300;

uint32_t last_id = 0;
uint32_t current_id = 0;
uint16_t last_read_time = 0;

void setup()
{
  Serial.begin(115200);
  rdm6300.begin(RDM6300_RX_PIN);
}

void loop()
{
  /* if non-zero tag_id, update() returns true- a new tag is near! */
  if (rdm6300.update()){
    current_id = rdm6300.get_tag_id();
    if(current_id != last_id){
      Serial.print(current_id);
      last_id = current_id;
    }
  }
  
  if(millis() - last_read_time > 1500){   //if id is old forget about it
    last_id = 0;
  }
  
  delay(10);
}
