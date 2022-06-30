from PLL_Lib import Picoscope

# Python allows a certain freedom of formatting
# when it comes to listing arguments, which can be nicer to read
with Picoscope(
        time_per_sample='10micro_s',
        probe_10x=True,
        trigger_channel='a'
) as scope:
    times, voltages_a, voltages_b = scope.wait_for_key('a')

print(f'The maximum voltage on channel A was {max(voltages_a)}V.')