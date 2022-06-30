from PLL_Lib import Arduino, Picoscope

half_period = 500
with Arduino() as arduino:
    with Picoscope(time_per_sample='1micro_s', trigger_channel='a') as scope:
        scope.wait_for_key('s', 'Press to start experiment.')
        while True:
            arduino.send_code(half_period)
            scope.wait_for_key('n', 'Next frequency?')
            half_period += 5