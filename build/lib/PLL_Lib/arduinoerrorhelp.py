class WrongContextException(Exception):
    def __init__(self):
        super().__init__(""
                         "\nThe Arduino object should be used inside a 'with' statement. See examples provided.\nYour code should resemble: \n"
                         "with Arduino() as arduino:\n"
                         "      CODE GOES HERE, EG:\n"
                         "      arduino.send_code(25) \n"
                         "      ...\n"
                         "(You will likely want to nest 'with' statements for the Picoscope and Arduino inside one another\n"
                         "in order to use both simultaneously)")

class PortInUseException(Exception):
    def __init__(self, port):
        super().__init__(''
                      f'\nUnable to connect to arduino at {port} (PermissionError). Probably becase it is already in use. To fix:'
                      '\n - Check the arduino IDE is closed (this is most likely the problem).'
                      '\n - Check there are no other python scripts running at the same time. Use task manager to make sure.'
                      f'\n - Ensure port {port} refers to an Arduino and not some other device (e.g. a picoscope!)'
                      '\n - Disconnect and reconnect the arduino.'
                      '\n - Restart everything.'
                      '\n - If all the above fails your Arduino may be broken, get a new one.')

class WrongPortException(Exception):
    def __init__(self, port):
        super().__init__(''
                      f'\nUnable to find an arduino at {port} (FileNotFound). Probably becase the port name is wrong. To fix:'
                      '\n - Ensure an Arduino is in fact plugged in.'
                      f'\n - Ensure port {port} refers to an Arduino and not some other device (e.g. a picoscope!)'
                      '\n - Check the arduino IDE is closed.'
                      '\n - Check there are no other python scripts running at the same time. Use task manager to make sure.'
                      '\n - Disconnect and reconnect the arduino.'
                      '\n - Restart everything.'
                      '\n - If all the above fails your Arduino may be broken, get a new one.')

class UnexpectedConnectionException(Exception):
    def __init__(self, port):
        super().__init__(''
                      f'\nUnable to find/connect to an arduino at {port} (Unknown Error). To fix:'
                      '\n - Ensure an Arduino is in fact plugged in.'
                      '\n - If you specified a port, try not specifying the port: with Arduino() as arduino: ... '
                      f'\n - Ensure port {port} refers to an Arduino and not some other device (e.g. a picoscope!)'
                      '\n - Check the arduino IDE is closed.'
                      '\n - Check there are no other python scripts running at the same time. Use task manager to make sure.'
                      '\n - Disconnect and reconnect the arduino.'
                      '\n - Restart everything.'
                      '\n - If all the above fails your Arduino may be broken, get a new one.')

class CouldNotFindArduinoException(Exception):
    def __init__(self):
        super().__init__(''
                      f'\nUnable to find an arduino connected to the computer. To fix:'
                      '\n - Ensure an Arduino is in fact plugged in.'
                      '\n - Check the arduino IDE is closed.'
                      '\n - Check there are no other python scripts running at the same time. Use task manager to make sure.'
                      '\n - Disconnect and reconnect the arduino.'
                      "\n - Try specifiying the port explicily, eg: with Arduino(port = 'COM5') as arduino: ...  "
                         "(you should be able to see the port in the arduino IDE, and then remeber to close it)"
                      '\n - Restart everything.'
                      '\n - If all the above fails your Arduino may be broken, get a new one.')

class InvalidCodeException(Exception):
    def __init__(self, wrongarg, min_arg, max_arg):
        super().__init__(
            f"\nThe argument '{wrongarg}' is not a valid code. "
            f"You should provide an integer between {min_arg} and {max_arg} inclusive.")