import numpy as np
# You will need to install matplotlib with 'pip install matplotlib'
from matplotlib import pyplot as plt

# Retrieve the data from the hard drive
times = np.load('Times.npy')
voltages_array = np.load('Voltages_A.npy')

# Plot just the first trace
plt.plot(times, voltages_array[0])
# Take the point-wise mean of the traces
plt.plot(times, voltages_array.mean(axis = 0))

plt.xlabel('Times/s'), plt.ylabel('A Voltage/V')
plt.show()