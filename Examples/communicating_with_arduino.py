from PLL_Lib import Arduino
import time

# Connect to the Arduino
with Arduino() as arduino:
    # You can refer to 'arduino' anywhere inside this indented block.
    for i in range(10, 60, 5):
        print(f'Sending code {i}...')
        arduino.send_code(i)
        time.sleep(1)
# The arduino automatically disconnects at the end of this indented block.
print('Done!')