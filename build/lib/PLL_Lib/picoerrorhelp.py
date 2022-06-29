from functools import reduce

class CouldNotFindScopeException(Exception):
    def __init__(self):
        super().__init__(''
              '\nCould not find a picoscope to connect to. To fix:'
              '\n - Check a picoscope is connected'
              '\n - Check it is not being used by another program, such as the picoscope software'
              '\n - Try disconnecting and reconnecting the picoscope.')


class WrongContextException(Exception):
    def __init__(self):
        super().__init__(""
                         "\nThe Picoscope object should be used inside a 'with' statement. See examples provided.\nYour code should resemble: \n"
                         "with Picoscope() as scope:\n"
                         "      CODE GOES HERE, EG:\n"
                         "      times, voltages_A, voltages_B = scope.get_trace() \n"
                         "      ...\n"
                         "(You will likely want to nest 'with' statements for the Picoscope and Arduino inside one another\n"
                         "in order to use both simultaneously)")

close_warning = "The picoscope was not disconnected properly by the program. You may have to disconnect and reconnect before reusing."

def trigger_warning(rising_edge, trigger_channel):
    type = "rising edge" if rising_edge else "falling edge"
    return f"\nThe picoscope is collecting data. It may be waiting for a trigger event ({type} on channel {trigger_channel}). " \
           f"\nNo such events have been detected so far. Use ctrl-c if you would like to terminate the program."

wait_warning = "\nThe picoscope is collecting data. You may wish to use a shorter time between samples. \n" \
               "Press ctrl-c to abort the program if you would like."


class InvalidVoltageRangeException(Exception):
    def __init__(self, wrongarg, rightargs):
        super().__init__(
            f"\nThe argument '{wrongarg}' is not a valid voltage range. Valid arguments are: \n"
            + str(list(rightargs))[1:-1])

class InvalidTimePerSampleException(Exception):
    def __init__(self, wrongarg, rightargs):
        super().__init__(
            f"\nThe argument '{wrongarg}' is not a valid time per sample. Valid arguments are: \n"
            + reduce(lambda x,y:x + '\n' + y , rightargs) + \
            '\nBear in mind around 8000 samples will be taken.')

class LostConnectionException(Exception):
    def __init__(self):
        super().__init__(''
              '\nCommunication with picoscope failed. To fix:'
              '\n - Check a picoscope is connected'
              '\n - Check it is not being used by another program, such as the picoscope software'
              '\n - Try disconnecting and reconnecting the picoscope'
              '\n - Try inserting a delay in code using time.sleep before this line of code is executed.')


class InvalidTriggerVoltageException(Exception):
    def __init__(self, wrongvoltage, rightvoltage, rightvstring):
        super().__init__(
            f"\nThe argument '{wrongvoltage}' is not a valid voltage range. "
            f"\nBased on the voltage range specified, '{rightvstring}', the trigger voltage must be between {-rightvoltage} and {rightvoltage} (in volts).")


class InvalidTriggerChannelException(Exception):
    def __init__(self, wrongarg):
        super().__init__(
            f"\nThe argument '{wrongarg}' is not a valid key to wait for."
            f"\nYou should give a single-letter string, such as 'a', 'b' etc, but not 'q' as 'q' is reserved for stopping the program.")

class InvalidFrequencyException(Exception):
    def __init__(self, wrongarg, maxfreq):
        super().__init__(
            f"\nThe argument '{wrongarg}' is not a frequency for the signal generator."
            f"\nYou should give a number representing the frequency in Hz between 0 and {maxfreq}.")

class InvalidWavetypeException(Exception):
    def __init__(self, wrongarg, rightargs):
        super().__init__(
            f"\nThe argument '{wrongarg}' is not a valid wavetype. Valid arguments are: \n"
            + str(list(rightargs))[1:-1])

class InvalidSigGenVoltageException(Exception):
    def __init__(self, wrongmin, wrongmax, maxfreq):
        super().__init__(
            f"\nThe arguments '{wrongmin}' and '{wrongmax} are not a valid set of bounding voltages."
            f"\nYou should give two numbers, -{maxfreq} ≤ min_voltage ≤ max_voltage ≤ {maxfreq}, "
            f"\nrepresenting the range of voltages of the generated signal in V.")