from PLL_Lib import Picoscope
# It is conventional to import numpy with the abbreviated alias np
import numpy as np

# The number of traces to save
N = 100

with Picoscope(time_per_sample='1micro_s', probe_10x=True, trigger_channel='a') as scope:
    # We can use the initial trace to judge the proper shape of the arrays
    times, voltages_template, _ = scope.wait_for_key('s', 'Press to start experiment')
    # Create an empty 2D Array for the traces
    voltages_array_a = np.zeros((N,voltages_template.size))
    # Create another
    voltages_array_b = np.zeros_like(voltages_array_a)
    for i in range(N):
        # All captures will have the same set of sample times, so can ignore this
        # get_trace takes as an optional argument a message that is displayed in the bottom-left
        _, voltages_a, voltages_b = scope.get_trace(f'Capturing trace {i}...')
        # Store them into the 2D array
        voltages_array_a[i] = voltages_a
        voltages_array_b[i] = voltages_b

# Save to memory - be sure to change these names if you run an experiment twice
# or it will overwrite the existing files with no warning!
np.save('Times.npy',times)
np.save('Voltages_A.npy',voltages_array_a)
np.save('Voltages_B.npy',voltages_array_b)

print('Done!')