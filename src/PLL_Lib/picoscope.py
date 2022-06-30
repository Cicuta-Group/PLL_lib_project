import ctypes as ct
from PLL_Lib.ps2000 import ps2000 as ps
import PLL_Lib.picoerrorhelp as er
from PLL_Lib.display import ScopeDisplay
import warnings
import time
import numpy as np
from numbers import Number
from importlib.metadata import version
version = version('PLL_Lib')

voltage_range_strings = {
    '20mv': 1,
    '50mv': 2,
    '100mv': 3,
    '200mv': 4,
    '500mv': 5,
    '1v': 6,
    '2v': 7,
    '5v': 8,
    '10v': 9,
    '20v': 10,
}

voltage_ranges = [None, 0.02, 0.05, 0.1, 0.2,0.5, 1, 2, 5, 10]

time_units = {
    0: 1e-15,
    1: 1e-12,
    2: 1e-9,
    3: 1e-6,
    4: 1e-3,
    5: 1e0
}

time_per_sample_options = {
    '10ns': 1,
    '20ns': 2,
    '40ns': 3,
    '80ns': 4,
    '160ns': 5,
    '320ns': 6,
    '640ns': 7,
    '1micro_s': 8,
    '3micro_s': 9,
    '5micro_s': 10,
    '10micro_s': 11,
    '20micro_s': 12,
    '41micro_s': 13,
    '82micro_s': 14,
    '164micro_s': 15,
    '328micro_s': 16,
    '655micro_s': 17,
    '1ms': 18,
    '3ms': 19,
    '5ms': 20,
    '10ms': 21,
}

waveform_options = {
    'SINE': 0,
    'SQUARE':1,
    'TRIANGLE':2,
    'RAMP_UP':3,
    'RAMP_DOWN':4,
    'CONSTANT_VOLTAGE':5,
    'GAUSSIAN':6,
    'SINC':7,
    'HALF_SINE':8
}

max_adc = ct.c_int16(32767)
warning_threshold = 5
load_timeout = 7
MAX_FREQUENCY = 1e5
MAX_SIGGEN_VOLTAGE = 2


def check_success(result, exceptiontype=er.LostConnectionException, errValue=0):
    if result == errValue:
        raise exceptiontype()
    return result


class Picoscope:
    def _check_with(f):
        def wrapper(self, *args, **kwargs):
            if not self._used_in_with:
                raise er.WrongContextException()
            return f(self, *args, **kwargs)

        return wrapper

    def __init__(self, *, time_per_sample='5micro_s', voltage_range='1v', trigger_channel=None, trigger_voltage=None,
                 rising_edge=True, trigger_offset=10, show_display=True, probe_10x=False):
        '''
        Should not be initialised directly but rather used as a context manager inside a 'with' statement.
        All arguments are optional.
        :param time_per_sample: The time per sample, or temporal resolution, given as a string. Options are
        10ns, 20ns, 40ns, 80ns, 160ns, 320ns, 640ns, 1micro_s, 3micro_s, 5micro_s (Default), 10micro_s
        20micro_s, 41micro_s, 82micro_s, 164micro_s, 328micro_s, 655micro_s, 1ms, 3ms, 5ms, 10ms
        :param voltage_range: The voltage range, given as a string representing the maximum positive or negative voltage that can be measured.
        IMPORTANT: This should be set taking into account any voltage reduction due to the probe, regardless of whether the probe_10x option is active.
        Options are 20mv, 50mv, 100mv, 1v (Default), 2v, 5v, 10v, 20v.
        :param trigger_channel: None (Default) for no trigger, or 'a' or 'b' to trigger using that channel.
        :param trigger_voltage: The voltage threshold of the edge detection for the trigger. Should be within the specified voltage range.
        IMPORTANT: This should be set taking into account any voltage reduction due to the probe, regardless of whether the probe_10x option is active.
        Default is the voltage range/4.
        :param rising_edge: True (Default) for rising edge triggering. False for falling edge triggering.
        :param trigger_offset: The percentage of samples which are recorded before the trigger event.
        This should be an integer between 0 and 100. Default is 10.
        :param show_display: Whether to display the traces in a window. Default is True.
        :param probe_10x: If True, apply a 10x multiplier to the ouput voltages in the display window and output arrays.
        Does not affect the input voltage range or trigger voltage, which should be set as if this is not enabled.
        Default is False.
        '''
        self._used_in_with = False
        self._probe_comp = 10 if probe_10x else 1
        vr_lower = voltage_range.lower()
        if vr_lower not in voltage_range_strings:
            raise er.InvalidVoltageRangeException(voltage_range, voltage_range_strings.keys())
        self._voltage_range = voltage_range_strings[vr_lower]
        self._voltage_range_volts = voltage_ranges[self._voltage_range]
        if time_per_sample not in time_per_sample_options:
            raise er.InvalidTimePerSampleException(time_per_sample, time_per_sample_options)
        self._time_text, self._timebase = time_per_sample, time_per_sample_options[time_per_sample]

        self._trigger_channel = trigger_channel
        self._trigger_offset = ct.c_int16(0)
        if trigger_channel is not None:
            if trigger_channel.upper() not in ('A', 'B'):
                raise er.InvalidTriggerChannelException(trigger_channel)
            if not type(trigger_offset) is int and 0 <= trigger_offset <= 100:
                raise er.InvalidTriggerOffsetException(trigger_offset)
            self._trigger_offset = ct.c_int16(-trigger_offset)
            if trigger_voltage is None:
                trigger_voltage = self._voltage_range_volts/4
            self._trigger_voltage = trigger_voltage
            self._trigger_adc = int(max_adc.value * self._trigger_voltage / self._voltage_range_volts)
            if not -max_adc.value <= self._trigger_adc <= max_adc.value:
                raise er.InvalidTriggerVoltageException(self._trigger_voltage, self._voltage_range_volts, voltage_range)
            self._rising_edge = rising_edge

        self._show_display = show_display
        self._last_cap_time = -1

    def __enter__(self):
        self._used_in_with = True
        print(f'PLL_Lib version {version}: Connecting to Picoscope...')
        check_success(ps.ps2000_open_unit_async())
        self._chandle, progress = ct.c_int16(), ct.c_int16()
        start_time = time.time()
        while ps.ps2000_open_unit_progress(ct.byref(self._chandle), ct.byref(progress)) == 0:
            if time.time() - start_time > load_timeout: raise er.CouldNotFindScopeException()
        check_success(ps.ps2000PingUnit(self._chandle), er.CouldNotFindScopeException)
        print('Connected to Picoscope!')

        # self._chandle = check_success(ps.ps2000_open_unit(), er.CouldNotFindScopeException)
        # enabled = 1, coupling type = PS2000_DC = 1, analogue offset = 0 V, channel = PS2000_CHANNEL_A = 0
        check_success(ps.ps2000_set_channel(self._chandle, 0, 1, 1, self._voltage_range))
        # same except channel = PS2000_CHANNEL_B = 1
        check_success(ps.ps2000_set_channel(self._chandle, 1, 1, 1, self._voltage_range))
        if self._trigger_channel is not None:
            channel_index = {'A': 0, 'B': 1}[self._trigger_channel.upper()]
            # last two are offset (in percent) and auto delay (in ms)
            check_success(
                ps.ps2000_set_trigger(self._chandle, channel_index, self._trigger_adc, int(not self._rising_edge),
                                      self._trigger_offset, 0))

        self._timeInterval, self._timeUnits, self._oversample = ct.c_int32(), ct.c_int32(), ct.c_int16(1)
        maxSamplesReturn = ct.c_int32()
        check_success(ps.ps2000_get_timebase(self._chandle, self._timebase, 8000, ct.byref(self._timeInterval),
                                             ct.byref(self._timeUnits), self._oversample,
                                             ct.byref(maxSamplesReturn)))
        self._max_samples = maxSamplesReturn.value

        # Set up display
        self._capture_time = self._max_samples * self._timeInterval.value * 1e-9  # Uses ns by default
        trigger_time = -self._capture_time * self._trigger_offset.value / 100
        if self._show_display:
            self.display = ScopeDisplay(-self._voltage_range_volts * self._probe_comp,
                                        self._voltage_range_volts * self._probe_comp, -trigger_time,
                                        self._capture_time - trigger_time, self._time_text, self._max_samples,
                                        self._probe_comp,
                                        None if self._trigger_channel is None else self._trigger_voltage * self._probe_comp
                                        , 0)
        return self

    @_check_with
    def get_trace(self, status_text="Pass text using get_trace('status goes here')"):
        '''
        Capture a single trace, either immediately or next time the set trigger triggers.
        :param status_text: A message to display in the bottom left.
        :return: A tuple containing numpy arrays for the sample times, the A voltages, and the B voltages.
        '''
        oversample = ct.c_int16(1)
        cmaxSamples = ct.c_int32(self._max_samples)
        check_success(ps.ps2000PingUnit(self._chandle))
        timeIndisposedms = ct.c_int32()
        check_success(
            ps.ps2000_run_block(self._chandle, cmaxSamples, self._timebase, oversample, ct.byref(timeIndisposedms)))

        # Check for data collection to finish using ps5000aIsReady
        warned, start_time = False, time.time()

        while ps.ps2000_ready(self._chandle) == 0:
            if time.time() - start_time > warning_threshold and not warned:
                if self._trigger_channel is not None:
                    warnings.warn(er.trigger_warning(self._rising_edge, self._trigger_channel.upper()))
                else:
                    warnings.warn(er.wait_warning)
                warned = True
        time_buffer = (ct.c_int32 * self._max_samples)()
        bufferA = (ct.c_int16 * self._max_samples)()
        bufferB = (ct.c_int16 * self._max_samples)()
        overflow = ct.c_int16()

        check_success(ps.ps2000_get_times_and_values(self._chandle, ct.byref(time_buffer), ct.byref(bufferA),
                                                     ct.byref(bufferB), None, None,
                                                     ct.byref(overflow), self._timeUnits.value, cmaxSamples))
        captime = None
        if self._last_cap_time != -1:
            captime = time.time() - self._last_cap_time
        self._last_cap_time = time.time()

        if overflow.value != 0 and not self._show_display:
            warnings.warn('Overflow!')

        arr_A, arr_B = np.array(bufferA, dtype=int), np.array(bufferB, dtype=int)
        volts_A = arr_A * self._voltage_range_volts / max_adc.value * self._probe_comp
        volts_B = arr_B * self._voltage_range_volts / max_adc.value * self._probe_comp
        times = np.array(time_buffer) * time_units[self._timeUnits.value]
        if self._show_display:
            self.display.set_status(status_text)
            self.display.update(times, volts_A, volts_B, captime, overflow.value != 0)
        return times, volts_A, volts_B

    @_check_with
    def wait_for_key(self,key, status = "Provide message using wait_for_key('KEY', 'status goes here')"):
        '''
        Run the picoscope continuously until the given key is pressed.
        :param key: (Non-optional) A string containing a single letter of the alphabet other than q.
        :param status: A message to display whilst waiting.
        :return: The first set of sample data after the key is pressed.
        '''
        if not self._show_display:
            raise er.NoGUIException('wait_for_key')
        if not (type(key) is str and len(key) == 1 and ord('a') <= ord(key.lower()) <= ord('z') and key.lower() != 'q'):
            raise er.InvalidKeyExeption(key)
        self.display.wait_for_keycode(ord(key.lower()))
        times, va, vb = self.get_trace(f"Waiting for key '{key.lower()}'. {status}")
        while not self.display.done_waiting:
            times, va, vb = self.get_trace(f"Waiting for key '{key.lower()}'. {status}")
        return times, va, vb


    @_check_with
    def set_signal_generator(self, frequency, wavetype='SQUARE', min_voltage = -2, max_voltage = 2):
        '''
        Activate the signal generator on the Picoscope.
        :param frequency: (Non-optional) the frequency in Hz of the generated signal.
        A number between 0 and 100,000.
        :param wavetype: A string representing the kind of waveform to produce.
        Options are 'SINE', 'SQUARE' (Default), 'TRIANGLE',
        'RAMP_UP', 'RAMP_DOWN', 'CONSTANT_VOLTAGE', 'GAUSSIAN', 'SINC', 'HALF_SINE'.
        :param min_voltage: A number between -2 and 2 representing the minimum voltage in volts
        of the produced waveform. Must be <= max_voltage. Default is -2.
        :param max_voltage: A number between -2 and 2 representing the maximum voltage in volts
        of the produced waveform. Must be >= min_voltage. Default is 2.
        '''
        if not (isinstance(frequency,Number) and 0 <= frequency <= MAX_FREQUENCY):
            raise er.InvalidFrequencyException(frequency, MAX_FREQUENCY)

        if not wavetype in waveform_options:
            raise er.InvalidWavetypeException(wavetype,waveform_options.keys())

        wave_index = ct.c_int32(waveform_options[wavetype])

        if not -MAX_SIGGEN_VOLTAGE <= min_voltage <= max_voltage <= MAX_SIGGEN_VOLTAGE:
            raise er.InvalidSigGenVoltageException(min_voltage,max_voltage,MAX_SIGGEN_VOLTAGE)

        offset_microvolts = ct.c_int32(int(1e6 * (min_voltage + max_voltage)/2))
        pk_to_pk_microvolts = ct.c_uint32(int(1e6 * (max_voltage - min_voltage)))
        frequency = ct.c_float(frequency)
        check_success(ps.ps2000_set_sig_gen_built_in(self._chandle,offset_microvolts,pk_to_pk_microvolts,wave_index,
                                                     frequency,frequency,
                                                     ct.c_float(0),ct.c_float(0),
                                                     ct.c_int32(0),ct.c_uint32(0)))

    def __exit__(self, exc_type, exc_val, exc_tb):
        stopStatus = ps.ps2000_stop(self._chandle)
        closeStatus = ps.ps2000_close_unit(self._chandle)
        if stopStatus == 0 or closeStatus == 0:
            warnings.warn(er.close_warning)
        if self._show_display:
            self.display.close()
