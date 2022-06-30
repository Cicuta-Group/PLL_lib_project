int half_period = 100;

void setup() {
  Serial.begin(9600);
  pinMode(9, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    // This is the line of code required to receive an integer from the python script.
    long incomingCode = Serial.parseInt(); Serial.read();
    half_period = incomingCode;
  }
  // Basic implementation of a square wave oscillator.
  digitalWrite(9,HIGH);
  delayMicroseconds(half_period);
  digitalWrite(9,LOW);
  delayMicroseconds(half_period);
}