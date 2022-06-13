import ctypes
from PLL_Lib.ps2000 import ps2000 as ps
from PLL_Lib.functions import adc2mV, mV2adc
import PLL_Lib.errorhelp as er
import warnings
import time
import numpy as np

voltage_ranges = {
    '20mv': 1,
    '50mv': 2,
    '100mv': 3,
    '200mv': 4,
    '1v': 6,
    '2v': 7,
    '5v': 8,
    '10v': 9,
    '20v': 10,
}

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

max_adc = ctypes.c_int16(32767)
warning_threshold = 5


def check_success(result, exceptiontype=er.LostConnectionException):
    if result == 0:
        raise exceptiontype()
    return result


class Picoscope:
    def _check_with(f):
        def wrapper(self, *args, **kwargs):
            if not self._used_in_with:
                raise er.WrongContextException()
            return f(self, *args, **kwargs)

        return wrapper

    def __init__(self, *, time_per_sample='5micro_s', trigger_channel=None, voltage_range='10v', trigger_voltage=2.5,
                 rising_edge=True):
        self._used_in_with = False
        vr_lower = voltage_range.lower()
        if vr_lower not in voltage_ranges:
            raise er.InvalidVoltageRangeException(voltage_range, voltage_ranges.keys())
        self._voltage_range = voltage_ranges[vr_lower]
        if time_per_sample not in time_per_sample_options:
            raise er.InvalidTimePerSampleException(time_per_sample, time_per_sample_options)
        self._timebase = time_per_sample_options[time_per_sample]
        if trigger_channel is not None and trigger_channel.upper() not in ('A', 'B'):
            raise er.InvalidTriggerChannelException(trigger_channel)
        self._trigger_channel = trigger_channel
        self._trigger_adc = mV2adc(trigger_voltage * 1000, self._voltage_range, max_adc)
        if not 0 <= self._trigger_adc <= max_adc.value:
            raise er.InvalidTriggerVoltageException(trigger_voltage,
                                                    adc2mV([max_adc.value], self._voltage_range, max_adc)[0] / 1000
                                                    , voltage_range)
        self._rising_edge = rising_edge

    def __enter__(self):
        self._used_in_with = True
        self._chandle = check_success(ps.ps2000_open_unit(), er.CouldNotFindScopeException)
        # enabled = 1, coupling type = PS2000_DC = 1, analogue offset = 0 V, channel = PS2000_CHANNEL_A = 0
        check_success(ps.ps2000_set_channel(self._chandle, 0, 1, 1, self._voltage_range))
        # same except channel = PS2000_CHANNEL_B = 1
        check_success(ps.ps2000_set_channel(self._chandle, 1, 1, 1, self._voltage_range))
        if self._trigger_channel is not None:
            channel_index = {'a': 0, 'b': 1}[self._trigger_channel.lower()]
            # last two are offset (in percent) and auto delay (in ms)
            check_success(
                ps.ps2000_set_trigger(self._chandle, channel_index, self._trigger_adc, int(not self._rising_edge), 0,
                                      0))

        self._timeInterval, self._timeUnits, self._oversample = ctypes.c_int32(), ctypes.c_int32(), ctypes.c_int16(1)
        maxSamplesReturn = ctypes.c_int32()
        check_success(ps.ps2000_get_timebase(self._chandle, self._timebase, 8000, ctypes.byref(self._timeInterval),
                                             ctypes.byref(self._timeUnits), self._oversample,
                                             ctypes.byref(maxSamplesReturn)))
        self.max_samples = maxSamplesReturn.value
        return self

    @_check_with
    def get_trace(self):
        # self.max_samples = 2000
        oversample = ctypes.c_int16(1)
        cmaxSamples = ctypes.c_int32(self.max_samples)
        check_success(ps.ps2000PingUnit(self._chandle))
        timeIndisposedms = ctypes.c_int32()
        check_success(
            ps.ps2000_run_block(self._chandle, cmaxSamples, self._timebase, oversample, ctypes.byref(timeIndisposedms)))

        # Check for data collection to finish using ps5000aIsReady
        warned, start_time = False, time.time()

        while ps.ps2000_ready(self._chandle) == 0:
            if time.time() - start_time > warning_threshold and not warned:
                if self._trigger_channel is not None:
                    warnings.warn(er.trigger_warning(self._rising_edge, self._trigger_channel.upper()))
                else:
                    warnings.warn(er.wait_warning)
                warned = True
        time_buffer = (ctypes.c_int32 * self.max_samples)()
        bufferA = (ctypes.c_int16 * self.max_samples)()
        bufferB = (ctypes.c_int16 * self.max_samples)()
        overflow = ctypes.c_int16()

        check_success(ps.ps2000_get_times_and_values(self._chandle, ctypes.byref(time_buffer), ctypes.byref(bufferA),
                                                     ctypes.byref(bufferB), None, None,
                                                     ctypes.byref(overflow), self._timeUnits.value, cmaxSamples))
        millivolts_A = adc2mV(bufferA, self._voltage_range, max_adc)
        millivolts_B = adc2mV(bufferB, self._voltage_range, max_adc)

        return np.array(time_buffer) * time_units[self._timeUnits.value], np.array(millivolts_A) / 1000, np.array(
            millivolts_B) / 1000

    def __exit__(self, exc_type, exc_val, exc_tb):
        stopStatus = ps.ps2000_stop(self._chandle)
        closeStatus = ps.ps2000_close_unit(self._chandle)
        if stopStatus == 0 or closeStatus == 0:
            warnings.warn(er.close_warning)



